"""
TF-IDF Topic Analysis Service

This service handles:
- TF-IDF based topic extraction from query text
- Timeline-based incremental topic updates
- Database persistence of computed topics
- Efficient caching and retrieval
"""

import logging
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from src.models.query import Query
from src.models.topic_analytics import TopicAnalytics, TopicGenerationLog

logger = logging.getLogger(__name__)

class TFIDFTopicService:
    """
    TF-IDF based topic analysis service for query analytics
    """
    
    def __init__(self):
        """Initialize the TF-IDF topic service"""
        
        # TF-IDF configuration
        self.max_features = 1000
        self.ngram_range = (1, 2)  # Unigrams and bigrams
        self.min_df = 2  # Must appear in at least 2 queries
        self.max_df = 0.8  # Not in more than 80% of queries
        
        # Stop words for research queries
        self.stop_words = self._get_research_stop_words()
        
        # Technical terms to preserve
        self.preserve_terms = self._get_preserve_terms()
        
        logger.info("TF-IDF Topic Service initialized")

    def _get_research_stop_words(self) -> Set[str]:
        """Get comprehensive stop words for research queries"""
        return {
            # Question words
            'what', 'how', 'when', 'where', 'why', 'who', 'which', 'whose', 'whom',
            # Verbs
            'is', 'are', 'was', 'were', 'am', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'can', 'get', 'give', 'tell', 'use', 'make', 'take', 'come', 'go', 'see', 'know',
            'think', 'look', 'want', 'work', 'find', 'become', 'seem', 'feel', 'try', 'leave',
            'call', 'need', 'mean', 'understand', 'explain', 'show', 'help',
            # Articles and prepositions
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among',
            # Pronouns
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
            'mine', 'yours', 'ours', 'theirs', 'myself', 'yourself', 'himself', 'herself',
            'itself', 'ourselves', 'yourselves', 'themselves',
            # Common research words
            'type', 'types', 'kind', 'kinds', 'way', 'ways', 'method', 'methods', 'example',
            'examples', 'difference', 'differences', 'comparison', 'compare', 'versus', 'vs',
            'paper', 'papers', 'research', 'study', 'studies', 'analysis', 'result', 'results'
        }

    def _get_preserve_terms(self) -> Set[str]:
        """Get technical terms that should be preserved even if short"""
        return {
            'ai', 'ml', 'nlp', 'cnn', 'rnn', 'lstm', 'gru', 'gan', 'vae', 'bert', 'gpt',
            'api', 'sql', 'nosql', 'gpu', 'cpu', 'ram', 'ssd', 'hdd', 'url', 'uri',
            'http', 'https', 'rest', 'json', 'xml', 'csv', 'pdf', 'html', 'css',
            'js', 'py', 'r', 'go', 'c++', 'java', 'php', 'ruby', 'swift', 'kt',
            'ios', 'web', 'app', 'ui', 'ux', 'gui', 'cli', 'sdk', 'ide', 'git',
            'aws', 'gcp', 'azure', 'k8s', 'docker', 'ci', 'cd', 'devops'
        }

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess query text for TF-IDF analysis
        
        Args:
            text: Raw query text
            
        Returns:
            Cleaned and preprocessed text
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep spaces and hyphens
        text = re.sub(r'[^\w\s\-]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Filter words
        filtered_words = []
        for word in words:
            word = word.strip('-')  # Remove leading/trailing hyphens
            if (len(word) > 2 and word not in self.stop_words) or word in self.preserve_terms:
                if not word.isdigit():  # Skip pure numbers
                    filtered_words.append(word)
        
        return ' '.join(filtered_words)

    def extract_topics_tfidf(
        self, 
        query_texts: List[str], 
        max_topics: int = 50
    ) -> Tuple[List[Tuple[str, float]], TfidfVectorizer]:
        """
        Extract topics using TF-IDF analysis
        
        Args:
            query_texts: List of query text strings
            max_topics: Maximum number of topics to extract
            
        Returns:
            Tuple of (topics with scores, fitted vectorizer)
        """
        if not query_texts:
            return [], None
        
        # Preprocess all texts
        preprocessed_texts = [self._preprocess_text(text) for text in query_texts]
        
        # Filter out empty texts
        preprocessed_texts = [text for text in preprocessed_texts if text.strip()]
        
        if not preprocessed_texts:
            return [], None
        
        try:
            # Initialize TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                ngram_range=self.ngram_range,
                min_df=self.min_df,
                max_df=self.max_df,
                stop_words=None,  # We handle stop words in preprocessing
                lowercase=False,  # Already lowercased in preprocessing
                token_pattern=r'\b\w+\b'
            )
            
            # Fit and transform the texts
            tfidf_matrix = vectorizer.fit_transform(preprocessed_texts)
            
            # Get feature names (terms)
            feature_names = vectorizer.get_feature_names_out()
            
            # Calculate mean TF-IDF scores for each term
            mean_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
            
            # Create list of (term, score) pairs
            term_scores = list(zip(feature_names, mean_scores))
            
            # Sort by score in descending order
            term_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return top topics
            top_topics = term_scores[:max_topics]
            
            logger.info(f"Extracted {len(top_topics)} topics from {len(preprocessed_texts)} queries")
            
            return top_topics, vectorizer
            
        except Exception as e:
            logger.error(f"TF-IDF extraction failed: {str(e)}")
            return [], None

    def get_sample_questions(
        self, 
        topic: str, 
        query_data: List[Tuple[str, datetime]], 
        max_samples: int = 3
    ) -> List[str]:
        """
        Get sample questions containing the topic
        
        Args:
            topic: Topic term to search for
            query_data: List of (question, timestamp) tuples
            max_samples: Maximum number of sample questions
            
        Returns:
            List of sample questions
        """
        matching_questions = []
        
        # Handle both single words and phrases
        topic_words = topic.lower().split()
        
        for question, _ in query_data:
            if not question:
                continue
                
            question_lower = question.lower()
            
            # Check if all words in topic appear in question
            if all(word in question_lower for word in topic_words):
                # Truncate long questions
                display_question = question[:80] + "..." if len(question) > 80 else question
                matching_questions.append(display_question)
                
                if len(matching_questions) >= max_samples:
                    break
        
        return matching_questions

    def process_topics_timeline(
        self, 
        session: Session, 
        force_rebuild: bool = False
    ) -> Dict:
        """
        Process topics using timeline-based approach
        
        Args:
            session: Database session
            force_rebuild: Force complete rebuild of topics
            
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        
        try:
            # Get last processing log
            last_log = session.query(TopicGenerationLog).order_by(
                desc(TopicGenerationLog.last_processed_timestamp)
            ).first()
            
            if force_rebuild or not last_log:
                # First time or forced rebuild - process all queries
                logger.info("Processing all queries for topic generation")
                
                all_queries = session.query(Query.question, Query.created_at).filter(
                    Query.question.isnot(None),
                    Query.question != ""
                ).all()
                
                if not all_queries:
                    return {
                        "success": True,
                        "processed_queries": 0,
                        "topics_updated": 0,
                        "processing_time": time.time() - start_time,
                        "cache_hit": False
                    }
                
                # Extract topics using TF-IDF
                query_texts = [q.question for q in all_queries]
                topics_with_scores, _ = self.extract_topics_tfidf(query_texts, max_topics=100)
                
                if not topics_with_scores:
                    return {
                        "success": False,
                        "error": "Failed to extract topics",
                        "processing_time": time.time() - start_time
                    }
                
                # Clear existing topics
                session.query(TopicAnalytics).delete()
                session.commit()
                
                # Count occurrences and store topics
                topics_stored = 0
                for topic, tfidf_score in topics_with_scores:
                    # Count actual occurrences
                    query_count = sum(1 for q in all_queries 
                                    if self._topic_in_question(topic, q.question))
                    
                    if query_count >= 2:  # Minimum threshold
                        # Get sample questions
                        sample_questions = self.get_sample_questions(topic, all_queries)
                        
                        # Store topic
                        topic_record = TopicAnalytics(
                            topic=topic,
                            query_count=query_count,
                            tfidf_score=float(tfidf_score),
                            sample_questions=sample_questions
                        )
                        session.add(topic_record)
                        topics_stored += 1
                
                session.commit()
                
                # Log the processing
                log_record = TopicGenerationLog(
                    last_processed_timestamp=datetime.now(),
                    total_queries_processed=len(all_queries),
                    topics_generated=topics_stored,
                    processing_time=time.time() - start_time
                )
                session.add(log_record)
                session.commit()
                
                logger.info(f"Processed {len(all_queries)} queries, generated {topics_stored} topics")
                
                return {
                    "success": True,
                    "processed_queries": len(all_queries),
                    "topics_updated": topics_stored,
                    "processing_time": time.time() - start_time,
                    "cache_hit": False
                }
                
            else:
                # Incremental update - check for new queries
                last_timestamp = last_log.last_processed_timestamp
                
                new_queries = session.query(Query.question, Query.created_at).filter(
                    Query.created_at > last_timestamp,
                    Query.question.isnot(None),
                    Query.question != ""
                ).all()
                
                if not new_queries:
                    # No new queries - return cache hit
                    logger.info("No new queries found, using cached topics")
                    return {
                        "success": True,
                        "processed_queries": 0,
                        "topics_updated": 0,
                        "processing_time": time.time() - start_time,
                        "cache_hit": True
                    }
                
                # Process new queries
                logger.info(f"Processing {len(new_queries)} new queries for topic update")
                
                # Get existing topics
                existing_topics = {t.topic: t for t in session.query(TopicAnalytics).all()}
                
                # Extract topics from new queries
                new_query_texts = [q.question for q in new_queries]
                new_topics_with_scores, _ = self.extract_topics_tfidf(new_query_texts, max_topics=50)
                
                topics_updated = 0
                for topic, tfidf_score in new_topics_with_scores:
                    # Count occurrences in new queries
                    new_count = sum(1 for q in new_queries 
                                  if self._topic_in_question(topic, q.question))
                    
                    if new_count >= 1:  # At least one occurrence in new data
                        if topic in existing_topics:
                            # Update existing topic
                            existing_topic = existing_topics[topic]
                            existing_topic.query_count += new_count
                            existing_topic.tfidf_score = float(
                                (existing_topic.tfidf_score + tfidf_score) / 2
                            )
                            existing_topic.last_updated = datetime.now()
                            
                            # Update sample questions
                            new_samples = self.get_sample_questions(topic, new_queries, max_samples=2)
                            if new_samples:
                                # Merge with existing samples, keeping max 3
                                all_samples = list(existing_topic.sample_questions) + new_samples
                                existing_topic.sample_questions = list(set(all_samples))[:3]
                            
                            topics_updated += 1
                        else:
                            # New topic
                            sample_questions = self.get_sample_questions(topic, new_queries)
                            
                            new_topic = TopicAnalytics(
                                topic=topic,
                                query_count=new_count,
                                tfidf_score=float(tfidf_score),
                                sample_questions=sample_questions
                            )
                            session.add(new_topic)
                            topics_updated += 1
                
                session.commit()
                
                # Update processing log
                new_log = TopicGenerationLog(
                    last_processed_timestamp=datetime.now(),
                    total_queries_processed=last_log.total_queries_processed + len(new_queries),
                    topics_generated=len(session.query(TopicAnalytics).all()),
                    processing_time=time.time() - start_time
                )
                session.add(new_log)
                session.commit()
                
                logger.info(f"Updated {topics_updated} topics from {len(new_queries)} new queries")
                
                return {
                    "success": True,
                    "processed_queries": len(new_queries),
                    "topics_updated": topics_updated,
                    "processing_time": time.time() - start_time,
                    "cache_hit": False
                }
                
        except Exception as e:
            logger.error(f"Topic processing failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }

    def _topic_in_question(self, topic: str, question: str) -> bool:
        """
        Check if topic appears in question
        
        Args:
            topic: Topic term (can be phrase)
            question: Question text
            
        Returns:
            True if topic appears in question
        """
        if not question:
            return False
        
        topic_lower = topic.lower()
        question_lower = question.lower()
        
        # For single words, check word boundaries
        if ' ' not in topic_lower:
            return re.search(r'\b' + re.escape(topic_lower) + r'\b', question_lower) is not None
        else:
            # For phrases, check if all words appear
            topic_words = topic_lower.split()
            return all(re.search(r'\b' + re.escape(word) + r'\b', question_lower) 
                      for word in topic_words)

    def get_top_topics(self, session: Session, limit: int = 10) -> List[Dict]:
        """
        Get top topics from database
        
        Args:
            session: Database session
            limit: Number of topics to return
            
        Returns:
            List of topic dictionaries
        """
        topics = session.query(TopicAnalytics).order_by(
            desc(TopicAnalytics.tfidf_score)
        ).limit(limit).all()
        
        return [
            {
                "topic": topic.topic,
                "query_count": topic.query_count,
                "tfidf_score": round(topic.tfidf_score, 4),
                "sample_questions": topic.sample_questions or [],
                "last_updated": topic.last_updated
            }
            for topic in topics
        ]