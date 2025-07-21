# app.py - Fixed Streamlit application for cloud deployment with Claude Sonnet
import streamlit as st
import anthropic
import requests
import json
import os
from typing import List, Dict
import time
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import tempfile
import subprocess
import numpy as np
import zipfile
import traceback

# Try to import MoviePy with fallback
try:
    from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, TextClip
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    MOVIEPY_AVAILABLE = False

# Configure page
st.set_page_config(
    page_title="AI Lesson Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better appearance
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stProgress .st-bo {
        background-color: #00ff00;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .step-container {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'lesson_data' not in st.session_state:
    st.session_state.lesson_data = {}
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = None
if 'slides_approved' not in st.session_state:
    st.session_state.slides_approved = False

class LessonGenerator:
    def __init__(self, claude_key: str, elevenlabs_key: str):
        self.claude_key = claude_key
        self.elevenlabs_key = elevenlabs_key
        if claude_key:
            try:
                self.client = anthropic.Anthropic(api_key=claude_key)
            except Exception as e:
                st.error(f"Error initializing Claude client: {str(e)}")
                self.client = None
        else:
            self.client = None
        
    def test_connection(self) -> bool:
        """Test Claude API connection"""
        if not self.client:
            return False
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            return True
        except Exception as e:
            st.error(f"API connection test failed: {str(e)}")
            return False
    
    def extract_text_from_file(self, uploaded_file) -> str:
        """Extract text content from uploaded file"""
        try:
            if uploaded_file.type == "text/plain":
                return str(uploaded_file.read(), "utf-8")
            elif uploaded_file.type == "application/pdf":
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    return text
                except ImportError:
                    return "PDF support not available. Please use TXT files."
            elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                try:
                    from docx import Document
                    doc = Document(uploaded_file)
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                    return text
                except ImportError:
                    return "DOCX support not available. Please use TXT files."
            else:
                return "Unsupported file type. Please use TXT files."
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def get_interesting_facts(self, topic: str, content: str) -> str:
        """Get interesting facts about the topic using Claude Sonnet"""
        if not self.client:
            return "Error: Claude client not initialized"
            
        try:
            # Truncate content to avoid token limits
            content_preview = content[:1500] if len(content) > 1500 else content
            
            prompt = f"""Based on the topic "{topic}" and the following content, find 5-7 interesting and engaging facts that would captivate students:

Content: {content_preview}

Focus on:
- Surprising statistics
- Historical anecdotes
- Real-world applications
- Fun trivia
- Current relevance

Format as a numbered list with brief explanations."""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                return "Error: No response content received"
                
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error: Unable to connect to Claude API. Please check your internet connection and API key."
            st.error(error_msg)
            print(f"Full error: {traceback.format_exc()}")
            return error_msg
        except requests.exceptions.Timeout:
            error_msg = "Timeout error: Claude API request timed out. Please try again."
            st.error(error_msg)
            print(f"Full error: {traceback.format_exc()}")
            return error_msg
        except anthropic.AuthenticationError:
            error_msg = "Authentication error: Invalid Claude API key. Please check your API key."
            st.error(error_msg)
            return error_msg
        except anthropic.RateLimitError:
            error_msg = "Rate limit error: Too many requests. Please wait a moment and try again."
            st.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error creating outline: {str(e)}"
            st.error(error_msg)
            print(f"Full error: {traceback.format_exc()}")
            return error_msg
        except Exception as e:
            error_msg = f"Error generating facts: {str(e)}"
            st.error(error_msg)
            print(f"Full error: {traceback.format_exc()}")
            return error_msg
    
    def create_lesson_outline(self, objectives: str, content: str, facts: str) -> str:
        """Create a comprehensive lesson outline using Claude Sonnet"""
        if not self.client:
            return "Error: Claude client not initialized"
            
        try:
            # Truncate content to avoid token limits
            content_preview = content[:1200] if len(content) > 1200 else content
            facts_preview = facts[:800] if len(facts) > 800 else facts
            
            prompt = f"""Create a detailed lesson outline based on:

Learning Objectives: {objectives}
Content Material: {content_preview}
Interesting Facts: {facts_preview}

Structure the lesson with:
1. Introduction (5-10 minutes)
2. Main content sections (3-4 sections, 10-15 minutes each)
3. Interactive elements/activities
4. Conclusion and review (5-10 minutes)

Include timing estimates and key talking points for each section."""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1200,
                temperature=0.6,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                return "Error: No response content received"
                
        except requests.exceptions.ConnectionError:
            error_msg = "Connection error: Unable to connect to Claude API. Please check your internet connection and API key."
            st.error(error_msg)
            print(f"Full error: {traceback.format_exc()}")
            return error_msg
        except requests.exceptions.Timeout:
            error_msg = "Timeout error: Claude API request timed out. Please try again."
            st.error(error_msg)
            print(f"Full error: {traceback.format_exc()}")
            return error_msg
        except anthropic.AuthenticationError:
            error_msg = "Authentication error: Invalid Claude API key. Please check your API key."
            st.error(error_msg)
            return error_msg
        except anthropic.RateLimitError:
            error_msg = "Rate limit error: Too many requests. Please wait a moment and try again."
            st.error(error_msg)
            return error_msg
    
    def generate_slide_content(self, outline: str, objectives: str) -> List[Dict]:
        """Generate content for individual slides using Claude Sonnet"""
        if not self.client:
            return self._get_fallback_slides()
            
        try:
            # Truncate to manage token limits
            outline_preview = outline[:1000] if len(outline) > 1000 else outline
            objectives_preview = objectives[:500] if len(objectives) > 500 else objectives
            
            prompt = f"""Based on this lesson outline and objectives, create content for 6 PowerPoint slides:

Outline: {outline_preview}
Objectives: {objectives_preview}

For each slide, provide:
1. Slide title (short and clear)
2. Key bullet points (3-4 points max, each point should be concise)
3. Speaker notes (2-3 sentences explaining what the teacher should say)
4. Suggested image description for visual aid

Return ONLY valid JSON in this exact format:
[
    {{
        "slide_number": 1,
        "title": "Introduction",
        "content": ["Welcome to the lesson", "Today's objectives", "What we'll discover"],
        "speaker_notes": "Welcome students and introduce the lesson objectives. Set expectations for what they will learn.",
        "image_description": "Welcoming classroom scene"
    }},
    {{
        "slide_number": 2,
        "title": "Main Topic Overview",
        "content": ["Key concept 1", "Key concept 2", "Why this matters"],
        "speaker_notes": "Explain the main concepts and their relevance to students' lives.",
        "image_description": "Educational diagram or illustration"
    }}
]

Keep each content point under 10 words. Keep speaker notes concise but informative."""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.6,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            if not response.content or len(response.content) == 0:
                st.warning("No content received from Claude. Using fallback slides.")
                return self._get_fallback_slides()
            
            # Parse JSON response
            content = response.content[0].text.strip()
            
            # Clean up the response
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            try:
                slides_content = json.loads(content)
                
                # Validate the structure
                if not isinstance(slides_content, list):
                    raise ValueError("Response is not a list")
                
                for slide in slides_content:
                    if not all(key in slide for key in ['slide_number', 'title', 'content', 'speaker_notes', 'image_description']):
                        raise ValueError("Missing required slide fields")
                
                return slides_content
                
            except json.JSONDecodeError as e:
                st.warning(f"JSON parsing error: {str(e)}. Using fallback slides.")
                print(f"Raw response: {content}")
                return self._get_fallback_slides()
                
        except requests.exceptions.ConnectionError:
            st.error("Connection error: Unable to connect to Claude API. Please check your internet connection and API key.")
            print(f"Full error: {traceback.format_exc()}")
            return self._get_fallback_slides()
        except requests.exceptions.Timeout:
            st.error("Timeout error: Claude API request timed out. Please try again.")
            print(f"Full error: {traceback.format_exc()}")
            return self._get_fallback_slides()
        except anthropic.AuthenticationError:
            st.error("Authentication error: Invalid Claude API key. Please check your API key.")
            return self._get_fallback_slides()
        except anthropic.RateLimitError:
            st.error("Rate limit error: Too many requests. Please wait a moment and try again.")
            return self._get_fallback_slides()
        except Exception as e:
            st.error(f"Error generating slides: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")
            return self._get_fallback_slides()
    
    def _get_fallback_slides(self):
        """Return basic slide structure as fallback"""
        return [
            {
                "slide_number": 1,
                "title": "Introduction",
                "content": ["Welcome to the lesson", "Overview of objectives", "What we'll learn today"],
                "speaker_notes": "Welcome students and introduce the lesson objectives. Set expectations for what they will learn.",
                "image_description": "Welcoming classroom scene"
            },
            {
                "slide_number": 2,
                "title": "Main Topic",
                "content": ["Key concept introduction", "Important definitions", "Real-world examples"],
                "speaker_notes": "Introduce the main topic and provide clear definitions with relatable examples.",
                "image_description": "Educational diagram"
            },
            {
                "slide_number": 3,
                "title": "Deep Dive",
                "content": ["Detailed explanation", "Step-by-step process", "Interactive discussion"],
                "speaker_notes": "Dive deeper into the topic with detailed explanations and encourage student participation.",
                "image_description": "Detailed illustration"
            },
            {
                "slide_number": 4,
                "title": "Applications",
                "content": ["Real-world uses", "Career connections", "Daily life examples"],
                "speaker_notes": "Show students how this topic applies to real life and future careers.",
                "image_description": "Real-world application image"
            },
            {
                "slide_number": 5,
                "title": "Practice Activity",
                "content": ["Hands-on exercise", "Group discussion", "Problem solving"],
                "speaker_notes": "Engage students with practical activities to reinforce learning.",
                "image_description": "Students working together"
            },
            {
                "slide_number": 6,
                "title": "Summary & Review",
                "content": ["Key takeaways", "Questions for reflection", "Next steps"],
                "speaker_notes": "Summarize the main points and prepare students for future lessons.",
                "image_description": "Summary checklist"
            }
        ]
    
    def create_powerpoint(self, slides_data: List[Dict], lesson_title: str):
        """Create PowerPoint presentation"""
        try:
            prs = Presentation()
            
            # Title slide
            title_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(title_layout)
            title = slide.shapes.title
            subtitle = slide.placeholders[1]
            
            title.text = lesson_title
            subtitle.text = "AI-Generated Educational Content"
            
            # Content slides
            for slide_data in slides_data:
                bullet_layout = prs.slide_layouts[1]
                slide = prs.slides.add_slide(bullet_layout)
                
                title_shape = slide.shapes.title
                title_shape.text = slide_data['title']
                
                content_shape = slide.placeholders[1]
                text_frame = content_shape.text_frame
                text_frame.clear()
                
                for point in slide_data['content']:
                    p = text_frame.add_paragraph()
                    p.text = str(point)  # Ensure it's a string
                    p.level = 0
            
            # Save to BytesIO
            pptx_buffer = io.BytesIO()
            prs.save(pptx_buffer)
            pptx_buffer.seek(0)
            
            return pptx_buffer
            
        except Exception as e:
            st.error(f"Error creating PowerPoint: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")
            return None
    
    def generate_audio(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> bytes:
        """Generate audio using ElevenLabs API"""
        if not self.elevenlabs_key:
            return None
            
        try:
            # Truncate text if too long
            if len(text) > 500:
                text = text[:500] + "..."
                
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.content
            else:
                st.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            st.error("Audio generation timed out. Please try again.")
            return None
        except Exception as e:
            st.error(f"Error generating audio: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")
            return None
    
    def create_video(self, slides_data: List[Dict], audio_files: List[tuple], lesson_title: str, output_path: str) -> str:
        """Create video from slides and audio using MoviePy"""
        if not MOVIEPY_AVAILABLE:
            st.warning("⚠️ Video generation is not available in this environment.")
            st.info("💡 You can still download PowerPoint and audio files and combine them manually using video editing software.")
            return None
            
        try:
            # Import MoviePy functions here to avoid module-level import issues
            from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_videoclips
            
            with tempfile.TemporaryDirectory() as temp_dir:
                st.info("🎬 Creating video presentation...")
                
                # Create slide images
                image_paths = []
                for i, slide_data in enumerate(slides_data):
                    # Create slide image
                    img_width, img_height = 1280, 720
                    img = Image.new('RGB', (img_width, img_height), 'white')
                    draw = ImageDraw.Draw(img)
                    
                    # Use basic fonts (most reliable across platforms)
                    try:
                        # Try to use better fonts if available
                        title_font = ImageFont.truetype("arial.ttf", 48)
                        content_font = ImageFont.truetype("arial.ttf", 32)
                    except:
                        try:
                            # Fallback fonts for different systems
                            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 48)
                            content_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 32)
                        except:
                            # Final fallback
                            title_font = ImageFont.load_default()
                            content_font = ImageFont.load_default()
                    
                    # Draw title
                    title = slide_data['title']
                    try:
                        bbox = draw.textbbox((0, 0), title, font=title_font)
                        title_width = bbox[2] - bbox[0]
                    except:
                        title_width = len(title) * 30  # Rough estimate
                    
                    title_x = max(50, (img_width - title_width) // 2)
                    draw.text((title_x, 80), title, fill='black', font=title_font)
                    
                    # Draw content points
                    y_offset = 200
                    for point in slide_data['content']:
                        # Simple text wrapping
                        words = str(point).split()
                        lines = []
                        current_line = []
                        
                        for word in words:
                            test_line = ' '.join(current_line + [word])
                            try:
                                bbox = draw.textbbox((0, 0), test_line, font=content_font)
                                test_width = bbox[2] - bbox[0]
                            except:
                                test_width = len(test_line) * 20  # Rough estimate
                            
                            if test_width < img_width - 150:
                                current_line.append(word)
                            else:
                                if current_line:
                                    lines.append(' '.join(current_line))
                                current_line = [word]
                        
                        if current_line:
                            lines.append(' '.join(current_line))
                        
                        for line in lines:
                            draw.text((75, y_offset), f"• {line}", fill='black', font=content_font)
                            y_offset += 40
                        
                        y_offset += 15
                    
                    # Save image
                    img_path = os.path.join(temp_dir, f"slide_{i:03d}.png")
                    img.save(img_path)
                    image_paths.append(img_path)
                
                # Save audio files
                audio_paths = []
                for i, (filename, audio_content) in enumerate(audio_files):
                    if audio_content:  # Only save if audio content exists
                        audio_path = os.path.join(temp_dir, f"audio_{i:03d}.mp3")
                        with open(audio_path, 'wb') as f:
                            f.write(audio_content)
                        audio_paths.append(audio_path)
                    else:
                        audio_paths.append(None)
                
                # Create video clips
                video_clips = []
                
                for i, (img_path, audio_path) in enumerate(zip(image_paths, audio_paths)):
                    try:
                        if audio_path and os.path.exists(audio_path):
                            # Load audio to get duration
                            audio_clip = AudioFileClip(audio_path)
                            duration = max(4.0, audio_clip.duration)
                        else:
                            duration = 5.0  # Default duration if no audio
                            audio_clip = None
                        
                        # Create image clip
                        img_clip = (ImageSequenceClip([img_path], fps=1)
                                   .set_duration(duration)
                                   .resize((1280, 720)))
                        
                        # Combine image and audio
                        if audio_clip:
                            video_clip = img_clip.set_audio(audio_clip)
                        else:
                            video_clip = img_clip
                            
                        video_clips.append(video_clip)
                        
                        if audio_clip:
                            audio_clip.close()
                            
                    except Exception as e:
                        st.warning(f"Issue with slide {i+1}: {str(e)}")
                        continue
                
                if not video_clips:
                    st.error("No video clips were created successfully")
                    return None
                
                # Concatenate clips
                final_video = concatenate_videoclips(video_clips)
                
                # Write video with cloud-optimized settings
                final_video.write_videofile(
                    output_path,
                    fps=24,
                    codec='libx264',
                    audio_codec='aac',
                    verbose=False,
                    logger=None,
                    preset='ultrafast'
                )
                
                # Clean up
                final_video.close()
                for clip in video_clips:
                    clip.close()
                
                return output_path
                
        except ImportError:
            st.warning("⚠️ MoviePy is not properly installed for video generation.")
            st.info("💡 PowerPoint and audio files are still available for download.")
            return None
        except Exception as e:
            st.error(f"Error creating video: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")
            return None

def main():
    # Header
    st.title("🎓 AI-Powered Lesson Generator")
    st.markdown("### Transform your teaching materials into engaging multimedia lessons")
    
    # Display deployment info
    st.markdown("""
    <div class="info-box">
        🌐 <strong>Deployed on Streamlit Cloud</strong> - Professional lesson generation powered by Claude Sonnet AI<br>
        📄 Generate PowerPoint presentations and audio narration instantly!
    </div>
    """, unsafe_allow_html=True)
    
    # Show MoviePy status
    if not MOVIEPY_AVAILABLE:
        st.markdown("""
        <div style="padding: 0.5rem; border-radius: 0.5rem; background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; margin: 1rem 0;">
            ⚠️ <strong>Note:</strong> Video generation is not available in this environment. You'll still get PowerPoint slides and audio files!
        </div>
        """, unsafe_allow_html=True)
    
    # Sidebar for API keys and settings
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Keys section
        with st.expander("🔐 API Keys", expanded=True):
            claude_key = st.text_input(
                "Anthropic Claude API Key", 
                type="password", 
                help="Get from: https://console.anthropic.com/",
                value=st.session_state.get('claude_key', '')
            )
            elevenlabs_key = st.text_input(
                "ElevenLabs API Key", 
                type="password", 
                help="Get from: https://elevenlabs.io/",
                value=st.session_state.get('elevenlabs_key', '')
            )
            
            # Store keys in session state
            if claude_key:
                st.session_state.claude_key = claude_key
            if elevenlabs_key:
                st.session_state.elevenlabs_key = elevenlabs_key
        
        if not claude_key or not elevenlabs_key:
            st.warning("⚠️ Please enter both API keys to continue")
            with st.expander("📝 How to get API keys"):
                st.markdown("""
                **Anthropic Claude API Key:**
                1. Go to [Anthropic Console](https://console.anthropic.com/)
                2. Sign up or log in
                3. Navigate to API Keys section
                4. Create a new API key
                5. Copy and paste it above
                
                **ElevenLabs API Key:**
                1. Go to [ElevenLabs](https://elevenlabs.io/)
                2. Sign up for free account
                3. Go to your profile settings
                4. Copy your API key
                """)
            return
        
        # Progress tracking
        st.header("📊 Progress")
        progress_steps = [
            "Input & Upload",
            "Content Analysis", 
            "Review & Approve",
            "Generate Materials",
            "Final Output"
        ]
        
        for i, step in enumerate(progress_steps, 1):
            if i < st.session_state.current_step:
                st.success(f"✅ {step}")
            elif i == st.session_state.current_step:
                st.info(f"🔄 {step}")
            else:
                st.write(f"⏳ {step}")
        
        # About section
        with st.expander("ℹ️ About"):
            st.markdown("""
            This app generates complete lesson materials including:
            - 📄 PowerPoint presentations
            - 🎵 Audio narration
            - 🎬 Complete video lessons
            
            Built with ❤️ using Streamlit, Claude Sonnet, and ElevenLabs.
            """)
    
    # Initialize lesson generator
    if claude_key and elevenlabs_key:
        lesson_gen = LessonGenerator(claude_key, elevenlabs_key)
        
        # Test API connection
        with st.sidebar:
            if st.button("🔍 Test API Connection"):
                with st.spinner("Testing Claude API connection..."):
                    if lesson_gen.test_connection():
                        st.success("✅ Claude API connection successful!")
                    else:
                        st.error("❌ Claude API connection failed!")
    else:
        return
    
    # Main content area
    main_container = st.container()
    
    with main_container:
        # Step 1: Input Collection
        if st.session_state.current_step == 1:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("📝 Step 1: Lesson Setup")
            
            col1, col2 = st.columns(2)
            
            with col1:
                lesson_title = st.text_input(
                    "Lesson Title", 
                    placeholder="e.g., Introduction to Photosynthesis",
                    value=st.session_state.lesson_data.get('title', '')
                )
                subject = st.selectbox(
                    "Subject", 
                    ["Science", "Math", "History", "English", "Social Studies", "Other"],
                    index=0
                )
                grade_level = st.selectbox(
                    "Grade Level", 
                    ["Elementary", "Middle School", "High School", "College"],
                    index=2
                )
            
            with col2:
                duration = st.slider("Lesson Duration (minutes)", 10, 60, 30)
                objectives = st.text_area(
                    "Learning Objectives", 
                    placeholder="What should students learn by the end of this lesson?",
                    height=150,
                    value=st.session_state.lesson_data.get('objectives', '')
                )
            
            st.subheader("📎 Upload Learning Material")
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=['txt'],
                help="Upload your lesson content, notes, or reference material (TXT format recommended for cloud deployment)"
            )
            
            # Quick demo option
            demo_section = st.expander("🚀 Quick Demo (No upload required)")
            with demo_section:
                st.info("Try the app instantly with pre-loaded content!")
                
                if st.checkbox("Use Demo Content: Renewable Energy Lesson"):
                    lesson_title = "Introduction to Renewable Energy"
                    objectives = "Students will understand different types of renewable energy sources and their benefits for the environment."
                    demo_content = """
                    Renewable energy comes from natural resources that are constantly replenished, such as sunlight, wind, rain, tides, waves, and geothermal heat. Unlike fossil fuels, renewable energy sources produce little to no greenhouse gases or pollutants.

                    Types of Renewable Energy:
                    1. Solar Energy - Captured using solar panels that convert sunlight into electricity through photovoltaic cells
                    2. Wind Energy - Generated by wind turbines that harness kinetic energy from moving air
                    3. Hydroelectric Power - Uses flowing or falling water to spin turbines and generate electricity
                    4. Geothermal Energy - Harnesses heat from the Earth's core for heating and electricity generation
                    5. Biomass - Uses organic materials like wood, agricultural waste, and algae for fuel

                    Benefits include reduced carbon emissions, energy independence, job creation in green industries, and sustainable development for future generations. The renewable energy sector has grown rapidly, with costs dropping significantly over the past decade.
                    """
                    
                    if st.button("🎯 Generate Demo Lesson", type="primary"):
                        with st.spinner("Creating demo lesson..."):
                            try:
                                facts = lesson_gen.get_interesting_facts(lesson_title, content)
                            
                            st.session_state.lesson_data = {
                                'title': lesson_title,
                                'subject': subject,
                                'grade_level': grade_level,
                                'duration': duration,
                                'objectives': objectives,
                                'content': content,
                                'facts': facts
                            }
                            st.session_state.current_step = 2
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error processing content: {str(e)}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Step 2: Content Analysis and Review
        elif st.session_state.current_step == 2:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("🔍 Step 2: Content Analysis & Review")
            
            data = st.session_state.lesson_data
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📚 Extracted Content Preview")
                content_preview = data.get('content', '')[:500] + "..." if len(data.get('content', '')) > 500 else data.get('content', '')
                st.text_area("Content", content_preview, height=200, disabled=True)
                
            with col2:
                st.subheader("🎯 Interesting Facts Generated")
                facts_content = data.get('facts', 'No facts generated yet.')
                st.markdown(facts_content)
            
            st.subheader("📋 Lesson Overview")
            with st.expander("Review Lesson Details", expanded=True):
                st.write(f"**Title:** {data.get('title', 'N/A')}")
                st.write(f"**Subject:** {data.get('subject', 'N/A')}")
                st.write(f"**Grade Level:** {data.get('grade_level', 'N/A')}")
                st.write(f"**Duration:** {data.get('duration', 'N/A')} minutes")
                st.write(f"**Objectives:** {data.get('objectives', 'N/A')}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("⬅️ Back to Edit", type="secondary"):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col2:
                if st.button("🔄 Regenerate Facts", type="secondary"):
                    with st.spinner("Regenerating facts..."):
                        try:
                            new_facts = lesson_gen.get_interesting_facts(data['title'], data['content'])
                            st.session_state.lesson_data['facts'] = new_facts
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error regenerating facts: {str(e)}")
            
            with col3:
                if st.button("✅ Create Lesson Outline", type="primary"):
                    with st.spinner("Creating lesson outline and slide content..."):
                        try:
                            outline = lesson_gen.create_lesson_outline(
                                data['objectives'], data['content'], data['facts']
                            )
                            
                            if outline.startswith("Error"):
                                st.error(outline)
                                return
                                
                            slides = lesson_gen.generate_slide_content(outline, data['objectives'])
                            
                            st.session_state.lesson_data['outline'] = outline
                            st.session_state.lesson_data['slides'] = slides
                            st.session_state.current_step = 3
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating outline: {str(e)}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Step 3: Review and Approve
        elif st.session_state.current_step == 3:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("👀 Step 3: Review & Approve Content")
            
            data = st.session_state.lesson_data
            
            st.subheader("📋 Lesson Outline")
            with st.expander("View Complete Outline", expanded=True):
                outline_content = data.get('outline', 'No outline generated yet.')
                st.markdown(outline_content)
            
            st.subheader("🖼️ Slide Previews")
            
            slides_data = data.get('slides', [])
            if slides_data:
                for slide in slides_data:
                    with st.expander(f"Slide {slide.get('slide_number', '?')}: {slide.get('title', 'Untitled')}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Content:**")
                            content_points = slide.get('content', [])
                            for point in content_points:
                                st.write(f"• {point}")
                            st.write(f"**Suggested Image:** {slide.get('image_description', 'No description')}")
                        
                        with col2:
                            st.write("**Speaker Notes:**")
                            st.write(slide.get('speaker_notes', 'No notes available'))
            else:
                st.warning("No slides generated. Please go back and regenerate content.")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("⬅️ Back to Analysis", type="secondary"):
                    st.session_state.current_step = 2
                    st.rerun()
            
            with col2:
                if st.button("🔄 Regenerate Slides", type="secondary"):
                    with st.spinner("Regenerating slide content..."):
                        try:
                            new_slides = lesson_gen.generate_slide_content(
                                data['outline'], data['objectives']
                            )
                            st.session_state.lesson_data['slides'] = new_slides
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error regenerating slides: {str(e)}")
            
            with col3:
                if st.button("✅ Approve & Generate Materials", type="primary"):
                    if slides_data:
                        st.session_state.slides_approved = True
                        st.session_state.current_step = 4
                        st.rerun()
                    else:
                        st.error("No slides to approve. Please regenerate slides first.")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Step 4: Generate Materials
        elif st.session_state.current_step == 4:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("🎬 Step 4: Generate Presentation Materials")
            
            data = st.session_state.lesson_data
            
            if not st.session_state.slides_approved:
                st.error("Please approve the content first")
                if st.button("⬅️ Back to Review"):
                    st.session_state.current_step = 3
                    st.rerun()
                return
            
            slides_data = data.get('slides', [])
            if not slides_data:
                st.error("No slides data available")
                if st.button("⬅️ Back to Review"):
                    st.session_state.current_step = 3
                    st.rerun()
                return
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Generate PowerPoint
                status_text.text("Creating PowerPoint presentation...")
                progress_bar.progress(20)
                
                pptx_buffer = lesson_gen.create_powerpoint(slides_data, data['title'])
                
                if not pptx_buffer:
                    st.error("Failed to create PowerPoint presentation")
                    return
                
                # Generate audio for each slide
                status_text.text("Generating audio narration...")
                progress_bar.progress(40)
                
                audio_files = []
                total_slides = len(slides_data)
                
                for i, slide in enumerate(slides_data):
                    status_text.text(f"Generating audio for slide {i+1}/{total_slides}...")
                    
                    speaker_notes = slide.get('speaker_notes', f"This is slide {i+1}: {slide.get('title', 'Untitled')}")
                    audio_content = lesson_gen.generate_audio(speaker_notes)
                    
                    if audio_content:
                        audio_files.append((f"slide_{i+1}.mp3", audio_content))
                    else:
                        # Add placeholder for failed audio generation
                        audio_files.append((f"slide_{i+1}.mp3", None))
                        st.warning(f"Failed to generate audio for slide {i+1}")
                    
                    progress_bar.progress(40 + (i+1) * 30 / total_slides)
                
                # Generate video (if MoviePy is available)
                video_path = None
                if MOVIEPY_AVAILABLE and any(audio for _, audio in audio_files if audio):
                    status_text.text("Creating final video presentation...")
                    progress_bar.progress(80)
                    
                    video_filename = f"{data['title'].replace(' ', '_')}_lesson.mp4"
                    video_path = os.path.join(tempfile.gettempdir(), video_filename)
                    
                    try:
                        final_video_path = lesson_gen.create_video(slides_data, audio_files, data['title'], video_path)
                        video_path = final_video_path
                    except Exception as e:
                        st.warning(f"Video generation failed: {str(e)}")
                        video_path = None
                
                progress_bar.progress(100)
                status_text.text("✅ Generation complete!")
                
                # Store results in session state
                st.session_state.pptx_buffer = pptx_buffer
                st.session_state.audio_files = audio_files
                st.session_state.video_path = video_path
                st.session_state.current_step = 5
                
                time.sleep(2)
                st.rerun()
                
            except Exception as e:
                st.error(f"Error during material generation: {str(e)}")
                print(f"Full error: {traceback.format_exc()}")
                
                # Provide option to go back
                if st.button("⬅️ Back to Review"):
                    st.session_state.current_step = 3
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Step 5: Final Output
        elif st.session_state.current_step == 5:
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            st.header("🎉 Step 5: Download Your Materials")
            
            st.markdown("""
            <div class="success-box">
                ✅ Your lesson materials have been generated successfully!
            </div>
            """, unsafe_allow_html=True)
            
            data = st.session_state.lesson_data
            
            # Summary
            with st.expander("📊 Lesson Summary", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Title", data.get('title', 'N/A'))
                    st.metric("Subject", data.get('subject', 'N/A'))
                    st.metric("Grade Level", data.get('grade_level', 'N/A'))
                with col2:
                    slides_count = len(data.get('slides', []))
                    audio_count = len([a for a in st.session_state.get('audio_files', []) if a[1] is not None])
                    st.metric("Slides Generated", slides_count)
                    st.metric("Audio Files", audio_count)
                    st.metric("Duration", f"{data.get('duration', 'N/A')} minutes")
            
            # Download section
            st.subheader("📥 Download Your Materials")
            
            # Main download buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if hasattr(st.session_state, 'pptx_buffer') and st.session_state.pptx_buffer:
                    st.download_button(
                        label="📄 Download PowerPoint",
                        data=st.session_state.pptx_buffer.getvalue(),
                        file_name=f"{data.get('title', 'lesson').replace(' ', '_')}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        help="Editable PowerPoint presentation"
                    )
                else:
                    st.error("PowerPoint file not available")
            
            with col2:
                if (hasattr(st.session_state, 'video_path') and 
                    st.session_state.video_path and 
                    os.path.exists(st.session_state.video_path)):
                    try:
                        with open(st.session_state.video_path, 'rb') as video_file:
                            video_data = video_file.read()
                            st.download_button(
                                label="🎬 Download Video",
                                data=video_data,
                                file_name=f"{data.get('title', 'lesson').replace(' ', '_')}_lesson.mp4",
                                mime="video/mp4",
                                help="Complete lesson video with narration"
                            )
                    except Exception as e:
                        st.error(f"Error reading video file: {str(e)}")
                else:
                    st.info("Video not available")
            
            with col3:
                if hasattr(st.session_state, 'audio_files') and st.session_state.audio_files:
                    # Create ZIP file with all audio files
                    try:
                        zip_buffer = io.BytesIO()
                        
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for filename, audio_content in st.session_state.audio_files:
                                if audio_content:  # Only add non-None audio content
                                    zip_file.writestr(filename, audio_content)
                        
                        zip_buffer.seek(0)
                        
                        if zip_buffer.getvalue():  # Check if ZIP has content
                            st.download_button(
                                label="🔊 Download Audio Files",
                                data=zip_buffer.getvalue(),
                                file_name=f"{data.get('title', 'lesson').replace(' ', '_')}_audio.zip",
                                mime="application/zip",
                                help="All narration audio files in ZIP format"
                            )
                        else:
                            st.info("No audio files available")
                    except Exception as e:
                        st.error(f"Error creating audio ZIP: {str(e)}")
                else:
                    st.info("Audio files not available")
            
            # Individual audio files section
            if hasattr(st.session_state, 'audio_files') and st.session_state.audio_files:
                available_audio = [af for af in st.session_state.audio_files if af[1] is not None]
                if available_audio:
                    with st.expander("🎵 Individual Audio Files"):
                        st.write("Download individual slide narrations:")
                        cols = st.columns(3)
                        for i, (filename, audio_content) in enumerate(available_audio):
                            col_idx = i % 3
                            with cols[col_idx]:
                                st.download_button(
                                    label=f"🔊 {filename}",
                                    data=audio_content,
                                    file_name=filename,
                                    mime="audio/mpeg",
                                    key=f"audio_{i}"
                                )
            
            # Status messages
            if hasattr(st.session_state, 'video_path') and st.session_state.video_path:
                st.success("🎉 Complete lesson video has been generated successfully!")
                st.info(f"📹 Video specs: {data.get('duration', 'N/A')} minutes | 1280x720 HD | MP4 format")
            else:
                st.warning("⚠️ Video generation had issues. PowerPoint and audio files are still available.")
            
            # Action buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Create Another Lesson", type="primary"):
                    # Reset session state
                    keys_to_keep = ['claude_key', 'elevenlabs_key']  # Keep API keys
                    for key in list(st.session_state.keys()):
                        if key not in keys_to_keep:
                            del st.session_state[key]
                    
                    # Reinitialize required session state
                    st.session_state.lesson_data = {}
                    st.session_state.current_step = 1
                    st.session_state.generated_content = None
                    st.session_state.slides_approved = False
                    
                    st.rerun()
            
            with col2:
                if st.button("📧 Share Feedback", type="secondary"):
                    st.info("💌 Love the app? Have suggestions? Let us know!")
            
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("Application encountered an unexpected error. Please refresh and try again.")
        st.error(f"Error details: {str(e)}")
        
        # Show helpful troubleshooting steps
        with st.expander("🔧 Troubleshooting Steps"):
            st.markdown("""
            **If you're seeing connection errors:**
            1. Check your internet connection
            2. Verify your Claude API key is correct and has credits
            3. Try refreshing the page
            4. Wait a few minutes and try again (rate limiting)
            
            **If you're seeing authentication errors:**
            1. Double-check your API key from https://console.anthropic.com/
            2. Make sure you have sufficient API credits
            3. Ensure your API key has the right permissions
            
            **If problems persist:**
            1. Try using the demo content first
            2. Use shorter text content
            3. Contact support if issues continue
            """)
        
        print(f"Application error: {traceback.format_exc()}")_gen.get_interesting_facts(lesson_title, demo_content)
                                
                                st.session_state.lesson_data = {
                                    'title': lesson_title,
                                    'subject': 'Science',
                                    'grade_level': 'High School',
                                    'duration': 30,
                                    'objectives': objectives,
                                    'content': demo_content,
                                    'facts': facts
                                }
                                st.session_state.current_step = 2
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error creating demo lesson: {str(e)}")
            
            # Process uploaded file
            if uploaded_file and lesson_title and objectives:
                if st.button("🚀 Analyze Content & Generate Facts", type="primary"):
                    with st.spinner("Processing your content..."):
                        try:
                            content = lesson_gen.extract_text_from_file(uploaded_file)
                            if content.startswith("Error"):
                                st.error(content)
                                return
                                
                            facts = lesson
