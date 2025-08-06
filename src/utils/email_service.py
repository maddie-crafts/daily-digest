"""
Email notification service for Daily Digest
"""
import asyncio
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

from ..processor.trending_analyzer import TrendingAnalyzer
from ..storage.database import DatabaseManager


@dataclass
class EmailConfig:
    """Email configuration settings"""
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    from_email: str
    from_name: str
    use_tls: bool = True


@dataclass
class EmailRecipient:
    """Email recipient information"""
    email: str
    name: str = ""
    subscribed: bool = True
    preferences: Dict[str, Any] = None


class EmailNotificationService:
    """Service for sending email notifications"""
    
    def __init__(self, email_config: EmailConfig, db_manager: DatabaseManager, 
                 templates_dir: str = "src/web/templates"):
        self.config = email_config
        self.db_manager = db_manager
        self.templates_dir = templates_dir
        self.logger = logging.getLogger('email_service')
        
        # Setup Jinja2 template environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Initialize trending analyzer
        self.trending_analyzer = TrendingAnalyzer(db_manager)
    
    async def send_trending_topics_email(self, recipients: List[EmailRecipient], 
                                       hours_back: int = 24, 
                                       base_url: str = "http://127.0.0.1:8000") -> Dict[str, Any]:
        """
        Send trending topics email to recipients
        
        Args:
            recipients: List of email recipients
            hours_back: Hours to look back for trending topics
            base_url: Base URL for links in email
            
        Returns:
            Dictionary with send results
        """
        try:
            # Get trending data
            trending_data = self.trending_analyzer.get_trending_summary(hours_back)
            
            if not recipients:
                return {
                    'success': False,
                    'error': 'No recipients provided',
                    'sent_count': 0
                }
            
            # Generate email content
            subject = self._generate_subject(trending_data)
            html_content = self._render_trending_email(trending_data, base_url)
            text_content = self._generate_text_version(trending_data, base_url)
            
            # Send emails
            results = await self._send_bulk_emails(
                recipients=recipients,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            # Log results
            self.logger.info(
                f"Trending topics email sent to {results['sent_count']}/{len(recipients)} recipients"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error sending trending topics email: {e}")
            return {
                'success': False,
                'error': str(e),
                'sent_count': 0
            }
    
    def _generate_subject(self, trending_data: Dict[str, Any]) -> str:
        """Generate email subject based on trending data"""
        if not trending_data['has_trends']:
            return "Daily Digest - No Major Trends Today"
        
        total_topics = trending_data['total_topics']
        if total_topics == 1:
            return "Daily Digest - 1 Trending Topic Today 🔥"
        else:
            return f"Daily Digest - {total_topics} Trending Topics Today 🔥"
    
    def _render_trending_email(self, trending_data: Dict[str, Any], base_url: str) -> str:
        """Render HTML email using Jinja2 template"""
        try:
            template = self.jinja_env.get_template('trending_email.html')
            return template.render(
                trending_data=trending_data,
                base_url=base_url,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        except Exception as e:
            self.logger.error(f"Error rendering email template: {e}")
            # Fallback to simple HTML
            return self._generate_fallback_html(trending_data, base_url)
    
    def _generate_text_version(self, trending_data: Dict[str, Any], base_url: str) -> str:
        """Generate plain text version of the email"""
        lines = [
            "DAILY DIGEST - TRENDING TOPICS",
            "=" * 35,
            ""
        ]
        
        if not trending_data['has_trends']:
            lines.extend([
                trending_data['message'],
                "",
                f"Browse all articles: {base_url}/",
                f"View analytics: {base_url}/analytics"
            ])
        else:
            lines.append(f"{trending_data['total_topics']} trending topics in the last {trending_data['time_period']}:")
            lines.append("")
            
            for i, topic in enumerate(trending_data['topics'], 1):
                lines.extend([
                    f"{i}. {topic['keyword'].upper()}",
                    f"   {topic['frequency']} mentions • {topic['articles_count']} articles • {topic['sentiment_label']}",
                    ""
                ])
                
                for article in topic['top_articles']:
                    lines.append(f"   • {article['title']} ({article['source']})")
                lines.append("")
            
            lines.extend([
                f"View full analytics: {base_url}/analytics",
                f"Browse all articles: {base_url}/"
            ])
        
        lines.extend([
            "",
            "---",
            "Daily Digest - Powered by AI",
            f"Unsubscribe: {base_url}/unsubscribe"
        ])
        
        return "\n".join(lines)
    
    def _generate_fallback_html(self, trending_data: Dict[str, Any], base_url: str) -> str:
        """Generate simple HTML fallback if template fails"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">Daily Digest - Trending Topics</h2>
        """
        
        if not trending_data['has_trends']:
            html += f"<p>{trending_data['message']}</p>"
        else:
            html += f"<p><strong>{trending_data['total_topics']}</strong> trending topics detected:</p><ul>"
            for topic in trending_data['topics']:
                html += f"<li><strong>{topic['keyword']}</strong> - {topic['frequency']} mentions</li>"
            html += "</ul>"
        
        html += f"""
            <p><a href="{base_url}/analytics">View Analytics</a> | <a href="{base_url}/">Browse Articles</a></p>
            <hr>
            <small>Daily Digest &copy; 2025</small>
        </body>
        </html>
        """
        return html
    
    async def _send_bulk_emails(self, recipients: List[EmailRecipient], 
                               subject: str, html_content: str, 
                               text_content: str) -> Dict[str, Any]:
        """Send emails to multiple recipients"""
        sent_count = 0
        failed_emails = []
        
        for recipient in recipients:
            if not recipient.subscribed:
                continue
                
            try:
                await self._send_single_email(
                    to_email=recipient.email,
                    to_name=recipient.name,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                sent_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to send email to {recipient.email}: {e}")
                failed_emails.append({
                    'email': recipient.email,
                    'error': str(e)
                })
                
            # Small delay to avoid overwhelming SMTP server
            await asyncio.sleep(0.1)
        
        return {
            'success': sent_count > 0,
            'sent_count': sent_count,
            'failed_count': len(failed_emails),
            'failed_emails': failed_emails
        }
    
    async def _send_single_email(self, to_email: str, to_name: str, 
                                subject: str, html_content: str, text_content: str):
        """Send a single email using aiosmtplib"""
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.config.from_name} <{self.config.from_email}>"
        msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
        msg['Subject'] = subject
        
        # Add text and HTML parts
        text_part = MIMEText(text_content, 'plain', 'utf-8')
        html_part = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email using aiosmtplib
        if self.config.use_tls:
            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                start_tls=True,
                username=self.config.username,
                password=self.config.password,
            )
        else:
            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                username=self.config.username,
                password=self.config.password,
            )
    
    def add_recipient(self, email: str, name: str = "", preferences: Dict[str, Any] = None) -> bool:
        """Add a new email recipient to the database"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO email_subscribers 
                    (email, name, subscribed, preferences, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    email, name, True, 
                    str(preferences) if preferences else None,
                    datetime.now(), datetime.now()
                ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error adding recipient {email}: {e}")
            return False
    
    def get_subscribers(self, active_only: bool = True) -> List[EmailRecipient]:
        """Get list of email subscribers"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT email, name, subscribed, preferences FROM email_subscribers"
                if active_only:
                    query += " WHERE subscribed = TRUE"
                
                cursor.execute(query)
                recipients = []
                
                for row in cursor.fetchall():
                    preferences = {}
                    if row['preferences']:
                        try:
                            preferences = eval(row['preferences'])
                        except:
                            preferences = {}
                    
                    recipients.append(EmailRecipient(
                        email=row['email'],
                        name=row['name'] or "",
                        subscribed=bool(row['subscribed']),
                        preferences=preferences
                    ))
                
                return recipients
        except Exception as e:
            self.logger.error(f"Error getting subscribers: {e}")
            return []
    
    def create_subscribers_table(self):
        """Create the email subscribers table if it doesn't exist"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS email_subscribers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        name TEXT,
                        subscribed BOOLEAN DEFAULT TRUE,
                        preferences TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscribers_email ON email_subscribers(email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_subscribers_subscribed ON email_subscribers(subscribed)')
                conn.commit()
                
                self.logger.info("Email subscribers table created/verified")
        except Exception as e:
            self.logger.error(f"Error creating subscribers table: {e}")
    
    async def send_test_email(self, test_email: str) -> Dict[str, Any]:
        """Send a test email to verify configuration"""
        try:
            test_recipient = EmailRecipient(
                email=test_email,
                name="Test User"
            )
            
            # Create sample trending data
            sample_trending_data = {
                'has_trends': True,
                'total_topics': 2,
                'time_period': '24 hours',
                'topics': [
                    {
                        'keyword': 'artificial intelligence',
                        'frequency': 15,
                        'articles_count': 5,
                        'sentiment_label': 'Positive',
                        'top_articles': [
                            {'title': 'AI Breakthrough in Medical Research', 'source': 'TechCrunch'},
                            {'title': 'New AI Model Shows Promise', 'source': 'BBC News'}
                        ]
                    },
                    {
                        'keyword': 'climate change',
                        'frequency': 12,
                        'articles_count': 4,
                        'sentiment_label': 'Neutral',
                        'top_articles': [
                            {'title': 'Climate Summit Reaches Agreement', 'source': 'Guardian'},
                            {'title': 'Renewable Energy Investments Rise', 'source': 'AP News'}
                        ]
                    }
                ]
            }
            
            subject = "[TEST] Daily Digest - Trending Topics Test"
            html_content = self._render_trending_email(sample_trending_data, "http://127.0.0.1:8000")
            text_content = self._generate_text_version(sample_trending_data, "http://127.0.0.1:8000")
            
            await self._send_single_email(
                to_email=test_email,
                to_name="Test User",
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            return {'success': True, 'message': f'Test email sent to {test_email}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}