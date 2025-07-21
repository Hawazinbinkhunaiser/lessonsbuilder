# app.py - Enhanced version with beautiful design
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

# Enhanced Custom CSS with beautiful design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;700&display=swap');
    
    /* Global Styles */
    .main > div {
        padding-top: 2rem;
    }
    
    /* Custom color palette */
    :root {
        --primary-purple: #6366f1;
        --primary-purple-dark: #4f46e5;
        --secondary-teal: #14b8a6;
        --accent-coral: #f97316;
        --accent-rose: #ec4899;
        --neutral-dark: #1f2937;
        --neutral-medium: #6b7280;
        --neutral-light: #f9fafb;
        --success-green: #10b981;
        --warning-amber: #f59e0b;
        --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        --gradient-secondary: linear-gradient(135deg, #14b8a6 0%, #06b6d4 100%);
        --gradient-warm: linear-gradient(135deg, #f97316 0%, #ec4899 100%);
    }
    
    /* Typography */
    .main-title {
        font-family: 'Playfair Display', serif;
        font-size: 3.5rem;
        font-weight: 700;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.5rem;
        line-height: 1.2;
    }
    
    .subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
        color: var(--neutral-medium);
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Hero section */
    .hero-container {
        background: var(--gradient-primary);
        border-radius: 24px;
        padding: 3rem 2rem;
        margin: 2rem 0;
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    
    .hero-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="50" cy="50" r="1" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
        opacity: 0.3;
    }
    
    .hero-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.5rem;
        font-weight: 700;
        color: white;
        margin-bottom: 1rem;
        position: relative;
        z-index: 1;
    }
    
    .hero-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        color: rgba(255, 255, 255, 0.9);
        margin-bottom: 0;
        position: relative;
        z-index: 1;
    }
    
    /* Card containers */
    .elegant-card {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(99, 102, 241, 0.1);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .elegant-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: var(--gradient-primary);
    }
    
    .elegant-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.12);
    }
    
    /* Status boxes */
    .status-success {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border: 1px solid #a7f3d0;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #065f46;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
    }
    
    .status-info {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 1px solid #93c5fd;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #1e3a8a;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
    }
    
    .status-warning {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border: 1px solid #fcd34d;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #92400e;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
    }
    
    /* Progress tracking */
    .progress-container {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    .progress-step {
        display: flex;
        align-items: center;
        padding: 0.75rem 0;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        border-radius: 8px;
        margin: 0.25rem 0;
        transition: all 0.2s ease;
    }
    
    .progress-step.completed {
        background: linear-gradient(135deg, #ecfdf5, #d1fae5);
        color: #065f46;
    }
    
    .progress-step.active {
        background: linear-gradient(135deg, #eff6ff, #dbeafe);
        color: #1e3a8a;
        transform: scale(1.02);
    }
    
    .progress-step.pending {
        background: #f9fafb;
        color: #6b7280;
    }
    
    /* Input styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        border-radius: 12px !important;
        border: 2px solid #e5e7eb !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: var(--primary-purple) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 12px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        padding: 0.75rem 2rem !important;
        transition: all 0.2s ease !important;
        border: none !important;
        text-transform: none !important;
    }
    
    .stButton > button[kind="primary"] {
        background: var(--gradient-primary) !important;
        color: white !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.3) !important;
    }
    
    .stButton > button[kind="secondary"] {
        background: white !important;
        color: var(--primary-purple) !important;
        border: 2px solid var(--primary-purple) !important;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: var(--primary-purple) !important;
        color: white !important;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e5e7eb;
        transition: all 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
    
    .metric-value {
        font-family: 'Inter', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary-purple);
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        color: var(--neutral-medium);
        font-weight: 500;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%) !important;
    }
    
    /* Expandable sections */
    .streamlit-expanderHeader {
        background: var(--gradient-secondary) !important;
        border-radius: 12px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        color: white !important;
    }
    
    /* File uploader styling */
    .stFileUploader > div {
        border-radius: 16px !important;
        border: 2px dashed var(--primary-purple) !important;
        background: linear-gradient(135deg, #f8fafc, #f1f5f9) !important;
        padding: 2rem !important;
        text-align: center !important;
    }
    
    /* Animation for loading states */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .loading-pulse {
        animation: pulse 2s infinite;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main-title {
            font-size: 2.5rem;
        }
        
        .hero-title {
            font-size: 2rem;
        }
        
        .elegant-card {
            padding: 1.5rem;
            margin: 1rem 0;
        }
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary-purple);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-purple-dark);
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
        self.client = anthropic.Anthropic(api_key=claude_key)
        
    def extract_text_from_file(self, uploaded_file) -> str:
        """Extract text content from uploaded file"""
        try:
            if uploaded_file.type == "text/plain":
                return str(uploaded_file.read(), "utf-8")
            else:
                return "Please use TXT files for best compatibility."
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def get_interesting_facts(self, topic: str, content: str) -> str:
        """Get interesting facts about the topic using Claude Sonnet"""
        try:
            prompt = f"""Based on the topic "{topic}" and the following content, find 5-7 interesting and engaging facts that would captivate students:

Content: {content[:2000]}

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
            return response.content[0].text
        except Exception as e:
            st.error(f"Error generating facts: {str(e)}")
            return f"Unable to generate facts due to API error. Please check your Claude API key and try again."
    
    def create_lesson_outline(self, objectives: str, content: str, facts: str) -> str:
        """Create a comprehensive lesson outline using Claude Sonnet"""
        try:
            prompt = f"""Create a detailed lesson outline based on:

Learning Objectives: {objectives}
Content Material: {content[:1500]}
Interesting Facts: {facts}

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
            return response.content[0].text
        except Exception as e:
            st.error(f"Error creating outline: {str(e)}")
            return f"Unable to generate lesson outline due to API error. Please check your Claude API key and try again."
    
    def generate_slide_content(self, outline: str, objectives: str) -> List[Dict]:
        """Generate content for individual slides using Claude Sonnet"""
        try:
            prompt = f"""Based on this lesson outline and objectives, create content for 6 PowerPoint slides:

Outline: {outline}
Objectives: {objectives}

For each slide, provide:
1. Slide title
2. Key bullet points (3-4 points max)
3. Speaker notes (what the teacher should say)
4. Suggested image description for visual aid

Return ONLY valid JSON in this exact format:
[
    {{
        "slide_number": 1,
        "title": "Slide Title",
        "content": ["Point 1", "Point 2", "Point 3"],
        "speaker_notes": "Detailed explanation for this slide...",
        "image_description": "Description of suggested image"
    }}
]

Keep speaker notes concise but informative (2-3 sentences per slide)."""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.6,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse JSON response
            content = response.content[0].text.strip()
            # Remove any markdown formatting
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            slides_content = json.loads(content)
            return slides_content
        except json.JSONDecodeError as e:
            st.error(f"Error parsing slide content JSON: {str(e)}")
            return self._get_fallback_slides()
        except Exception as e:
            st.error(f"Error generating slides: {str(e)}")
            return self._get_fallback_slides()
    
    def _get_fallback_slides(self) -> List[Dict]:
        """Return fallback slide structure when API fails"""
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
                "title": "Main Content",
                "content": ["Key concept overview", "Important details", "Real-world applications"],
                "speaker_notes": "Present the main content of the lesson with clear explanations and examples.",
                "image_description": "Educational diagram or illustration"
            },
            {
                "slide_number": 3,
                "title": "Summary and Review",
                "content": ["Key takeaways", "Important points to remember", "Questions for discussion"],
                "speaker_notes": "Summarize the lesson and encourage student questions and discussion.",
                "image_description": "Summary or conclusion visual"
            }
        ]

    def create_powerpoint(self, slides_data: List[Dict], lesson_title: str) -> io.BytesIO:
   
    try:
        from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE

        if not slides_data or not isinstance(slides_data, list):
            st.error("Invalid slide data provided")
            return None

        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

        # Custom theme color
        theme_bg_color = RGBColor(242, 246, 255)
        title_color = RGBColor(51, 51, 102)
        text_color = RGBColor(60, 60, 60)
        accent_color = RGBColor(99, 102, 241)

        # Title Slide
        title_slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
        slide = title_slide

        # Background rectangle
        shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        fill = shape.fill
        fill.solid()
        fill.fore_color.rgb = theme_bg_color
        shape.line.fill.background()

        # Title text
        title_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11), Inches(2))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = lesson_title
        run.font.size = Pt(48)
        run.font.bold = True
        run.font.color.rgb = title_color
        p.alignment = PP_ALIGN.CENTER

        subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(5), Inches(11), Inches(1))
        tf = subtitle_box.text_frame
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = "AI-Generated Educational Content"
        run.font.size = Pt(24)
        run.font.color.rgb = accent_color
        p.alignment = PP_ALIGN.CENTER

        # Content slides
        for slide_data in slides_data:
            slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

            # Background
            bg_shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
            bg_fill = bg_shape.fill
            bg_fill.solid()
            bg_fill.fore_color.rgb = theme_bg_color
            bg_shape.line.fill.background()

            # Header band
            header = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1))
            header.fill.solid()
            header.fill.fore_color.rgb = accent_color
            header.line.fill.background()

            header_tf = header.text_frame
            header_tf.clear()
            p = header_tf.paragraphs[0]
            run = p.add_run()
            run.text = slide_data.get("title", "Untitled")
            run.font.size = Pt(28)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)

            # Content bullets
            content_box = slide.shapes.add_textbox(Inches(1), Inches(1.3), Inches(11.5), Inches(5.5))
            tf = content_box.text_frame
            tf.word_wrap = True
            for point in slide_data.get("content", []):
                p = tf.add_paragraph()
                p.text = point
                p.font.size = Pt(20)
                p.font.color.rgb = text_color
                p.level = 0

        pptx_buffer = io.BytesIO()
        prs.save(pptx_buffer)
        pptx_buffer.seek(0)
        return pptx_buffer

    except Exception as e:
        st.error(f"Error creating beautiful PowerPoint: {str(e)}")
        return None
    
    def generate_audio(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> bytes:
        """Generate audio using ElevenLabs API"""
        try:
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
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                return response.content
            else:
                st.error(f"ElevenLabs API error: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Error generating audio: {str(e)}")
            return None

def main():
    # Beautiful Header
    st.markdown("""
    <div class="hero-container">
        <h1 class="hero-title">🎓 AI Lesson Generator</h1>
        <p class="hero-subtitle">Transform your teaching materials into engaging multimedia lessons with the power of AI</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display deployment info with enhanced styling
    st.markdown("""
    <div class="status-info">
        <strong>🌐 Deployed on Streamlit Cloud</strong><br>
        Professional lesson generation powered by Claude Sonnet AI - Create PowerPoint presentations and audio narration instantly!
    </div>
    """, unsafe_allow_html=True)
    
    # Show MoviePy status with enhanced styling
    if not MOVIEPY_AVAILABLE:
        st.markdown("""
        <div class="status-warning">
            ⚠️ <strong>Note:</strong> Video generation is not available in this environment. You'll still get PowerPoint slides and audio files!
        </div>
        """, unsafe_allow_html=True)
    
    # Enhanced Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #6366f1; font-family: 'Playfair Display', serif; margin-bottom: 0.5rem;">⚙️ Configuration</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # API Keys section with enhanced styling
        with st.expander("🔐 API Keys", expanded=True):
            claude_key = st.text_input(
                "Anthropic Claude API Key", 
                type="password", 
                help="Get from: https://console.anthropic.com/"
            )
            elevenlabs_key = st.text_input(
                "ElevenLabs API Key", 
                type="password", 
                help="Get from: https://elevenlabs.io/"
            )
        
        if not claude_key or not elevenlabs_key:
            st.markdown("""
            <div class="status-warning">
                ⚠️ Please enter both API keys to continue
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Enhanced Progress tracking
        st.markdown("<h3 style='color: #6366f1; font-family: Inter, sans-serif; margin: 1.5rem 0 1rem 0;'>📊 Progress</h3>", unsafe_allow_html=True)
        
        progress_steps = [
            ("📝", "Input & Upload"),
            ("🔍", "Content Analysis"), 
            ("👀", "Review & Approve"),
            ("🎬", "Generate Materials"),
            ("🎉", "Final Output")
        ]
        
        progress_html = '<div class="progress-container">'
        for i, (icon, step) in enumerate(progress_steps, 1):
            if i < st.session_state.current_step:
                status_class = "completed"
                status_icon = "✅"
            elif i == st.session_state.current_step:
                status_class = "active"
                status_icon = "🔄"
            else:
                status_class = "pending"
                status_icon = "⏳"
            
            progress_html += f'<div class="progress-step {status_class}">{status_icon} {icon} {step}</div>'
        progress_html += '</div>'
        
        st.markdown(progress_html, unsafe_allow_html=True)
    
    # Initialize lesson generator
    if claude_key and elevenlabs_key:
        lesson_gen = LessonGenerator(claude_key, elevenlabs_key)
    else:
        return
    
    # Main content area with enhanced styling
    main_container = st.container()
    
    with main_container:
        # Step 1: Input Collection
        if st.session_state.current_step == 1:
            st.markdown('<div class="elegant-card">', unsafe_allow_html=True)
            st.markdown("<h2 style='color: #6366f1; font-family: Playfair Display, serif; margin-bottom: 1.5rem;'>📝 Step 1: Lesson Setup</h2>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                lesson_title = st.text_input("Lesson Title", placeholder="e.g., Introduction to Photosynthesis")
                subject = st.selectbox("Subject", ["Science", "Math", "History", "English", "Social Studies", "Other"])
                grade_level = st.selectbox("Grade Level", ["Elementary", "Middle School", "High School", "College"])
            
            with col2:
                duration = st.slider("Lesson Duration (minutes)", 10, 60, 30)
                objectives = st.text_area("Learning Objectives", placeholder="What should students learn?", height=150)
            
            st.markdown("<h3 style='color: #14b8a6; font-family: Inter, sans-serif; margin: 2rem 0 1rem 0;'>📎 Upload Learning Material</h3>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Choose a file", type=['txt'], help="Upload TXT files only")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Enhanced Quick demo option
            with st.expander("🚀 Quick Demo", expanded=False):
                st.markdown("""
                <div style="background: linear-gradient(135deg, #f0f9ff, #e0f2fe); padding: 1.5rem; border-radius: 12px; margin: 1rem 0;">
                    <h4 style="color: #0369a1; margin-bottom: 1rem;">Try our sample lesson about Renewable Energy!</h4>
                </div>
                """, unsafe_allow_html=True)
                
                if st.checkbox("Use Demo Content: Renewable Energy Lesson"):
                    lesson_title = "Introduction to Renewable Energy"
                    objectives = "Students will understand different types of renewable energy sources and their benefits."
                    demo_content = """
                    Renewable energy comes from natural resources that are constantly replenished, such as sunlight, wind, rain, tides, waves, and geothermal heat. Unlike fossil fuels, renewable energy sources produce little to no greenhouse gases or pollutants.

                    Types of Renewable Energy:
                    1. Solar Energy - Captured using solar panels that convert sunlight into electricity
                    2. Wind Energy - Generated by wind turbines that harness wind power
                    3. Hydroelectric Power - Uses flowing water to generate electricity
                    4. Geothermal Energy - Harnesses heat from the Earth's core
                    5. Biomass - Uses organic materials like wood and agricultural waste for fuel

                    Benefits include reduced carbon emissions, energy independence, job creation, and sustainable development for future generations.
                    """
                    
                    if st.button("🎯 Generate Demo Lesson", type="primary"):
                        with st.spinner("✨ Creating your demo lesson..."):
                            facts = lesson_gen.get_interesting_facts(lesson_title, demo_content)
                            
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
            
            # Process uploaded file with enhanced UI
            if uploaded_file and lesson_title and objectives:
                if st.button("🚀 Analyze Content & Generate Facts", type="primary"):
                    with st.spinner("✨ Processing your content and generating insights..."):
                        content = lesson_gen.extract_text_from_file(uploaded_file)
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
        
        # Step 2: Content Analysis and Review
        elif st.session_state.current_step == 2:
            st.markdown('<div class="elegant-card">', unsafe_allow_html=True)
            st.markdown("<h2 style='color: #6366f1; font-family: Playfair Display, serif; margin-bottom: 1.5rem;'>🔍 Step 2: Content Analysis & Review</h2>", unsafe_allow_html=True)
            
            data = st.session_state.lesson_data
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("<h3 style='color: #14b8a6; font-family: Inter, sans-serif;'>📚 Extracted Content Preview</h3>", unsafe_allow_html=True)
                st.text_area("Content", data['content'][:500] + "...", height=200, disabled=True)
                
            with col2:
                st.markdown("<h3 style='color: #f97316; font-family: Inter, sans-serif;'>🎯 Interesting Facts Generated</h3>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #fefbf3, #fef3e2); padding: 1.5rem; border-radius: 12px; border-left: 4px solid #f97316;">
                    {data['facts']}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<h3 style='color: #6366f1; font-family: Inter, sans-serif; margin: 2rem 0 1rem 0;'>📋 Lesson Overview</h3>", unsafe_allow_html=True)
            
            # Enhanced lesson details display
            overview_cols = st.columns(4)
            with overview_cols[0]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">📖</div>
                    <div class="metric-label">{data['title']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with overview_cols[1]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">🎓</div>
                    <div class="metric-label">{data['subject']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with overview_cols[2]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">👥</div>
                    <div class="metric-label">{data['grade_level']}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with overview_cols[3]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{data['duration']}</div>
                    <div class="metric-label">Minutes</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid #e5e7eb; margin: 1rem 0;">
                <strong style="color: #6366f1;">Learning Objectives:</strong><br>
                <span style="color: #6b7280;">{data['objectives']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Action buttons with enhanced styling
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("⬅️ Back to Edit", type="secondary"):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col2:
                if st.button("🔄 Regenerate Facts", type="secondary"):
                    with st.spinner("🎲 Generating new fascinating facts..."):
                        new_facts = lesson_gen.get_interesting_facts(data['title'], data['content'])
                        st.session_state.lesson_data['facts'] = new_facts
                        st.rerun()
            
            with col3:
                if st.button("✅ Create Lesson Outline", type="primary"):
                    with st.spinner("🎨 Creating comprehensive lesson outline and slide content..."):
                        outline = lesson_gen.create_lesson_outline(data['objectives'], data['content'], data['facts'])
                        slides = lesson_gen.generate_slide_content(outline, data['objectives'])
                        
                        st.session_state.lesson_data['outline'] = outline
                        st.session_state.lesson_data['slides'] = slides
                        st.session_state.current_step = 3
                        st.rerun()
        
        # Step 3: Review and Approve
        elif st.session_state.current_step == 3:
            st.markdown('<div class="elegant-card">', unsafe_allow_html=True)
            st.markdown("<h2 style='color: #6366f1; font-family: Playfair Display, serif; margin-bottom: 1.5rem;'>👀 Step 3: Review & Approve Content</h2>", unsafe_allow_html=True)
            
            data = st.session_state.lesson_data
            
            st.markdown("<h3 style='color: #14b8a6; font-family: Inter, sans-serif;'>📋 Lesson Outline</h3>", unsafe_allow_html=True)
            with st.expander("View Complete Outline", expanded=True):
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f0fdfa, #ecfdf5); padding: 2rem; border-radius: 16px; border-left: 4px solid #14b8a6;">
                    {data['outline']}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<h3 style='color: #f97316; font-family: Inter, sans-serif; margin: 2rem 0 1rem 0;'>🖼️ Slide Previews</h3>", unsafe_allow_html=True)
            
            if 'slides' in data and data['slides']:
                for i, slide in enumerate(data['slides']):
                    with st.expander(f"Slide {slide['slide_number']}: {slide['title']}", expanded=i == 0):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**📝 Content:**")
                            for point in slide['content']:
                                st.markdown(f"• {point}")
                            st.markdown(f"**🖼️ Suggested Image:** {slide['image_description']}")
                        
                        with col2:
                            st.markdown("**🎤 Speaker Notes:**")
                            st.markdown(f"""
                            <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; font-style: italic;">
                                {slide['speaker_notes']}
                            </div>
                            """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("⬅️ Back to Analysis", type="secondary"):
                    st.session_state.current_step = 2
                    st.rerun()
            
            with col2:
                if st.button("🔄 Regenerate Slides", type="secondary"):
                    with st.spinner("🎨 Creating new slide variations..."):
                        new_slides = lesson_gen.generate_slide_content(data['outline'], data['objectives'])
                        st.session_state.lesson_data['slides'] = new_slides
                        st.rerun()
            
            with col3:
                if st.button("✅ Approve & Generate Materials", type="primary"):
                    st.session_state.slides_approved = True
                    st.session_state.current_step = 4
                    st.rerun()
        
        # Step 4: Generate Materials
        elif st.session_state.current_step == 4:
            st.markdown('<div class="elegant-card">', unsafe_allow_html=True)
            st.markdown("<h2 style='color: #6366f1; font-family: Playfair Display, serif; margin-bottom: 1.5rem;'>🎬 Step 4: Generate Presentation Materials</h2>", unsafe_allow_html=True)
            
            data = st.session_state.lesson_data
            
            if not st.session_state.slides_approved:
                st.error("Please approve the content first")
                return
            
            # Enhanced status tracking
            status_container = st.empty()
            
            # Generate PowerPoint with enhanced status messages
            status_container.markdown("""
            <div class="loading-pulse" style="background: linear-gradient(135deg, #eff6ff, #dbeafe); padding: 1.5rem; border-radius: 12px; border-left: 4px solid #3b82f6;">
                🔄 <strong>Creating PowerPoint presentation...</strong><br>
                <small>Designing beautiful slides with your content</small>
            </div>
            """, unsafe_allow_html=True)
            
            try:
                pptx_buffer = lesson_gen.create_powerpoint(data['slides'], data['title'])
            except Exception as e:
                st.error(f"Error creating PowerPoint: {str(e)}")
                pptx_buffer = None
            
            if pptx_buffer:
                status_container.markdown("""
                <div class="loading-pulse" style="background: linear-gradient(135deg, #f0fdfa, #ecfdf5); padding: 1.5rem; border-radius: 12px; border-left: 4px solid #10b981;">
                    🔄 <strong>Generating audio narration...</strong><br>
                    <small>Creating professional voice-over for your slides</small>
                </div>
                """, unsafe_allow_html=True)
                
                audio_files = []
                for i, slide in enumerate(data['slides']):
                    status_container.markdown(f"""
                    <div class="loading-pulse" style="background: linear-gradient(135deg, #fefbf3, #fef3e2); padding: 1.5rem; border-radius: 12px; border-left: 4px solid #f59e0b;">
                        🔄 <strong>Generating audio for slide {i+1} of {len(data['slides'])}...</strong><br>
                        <small>Processing: "{slide['title']}"</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    try:
                        speaker_notes = slide.get('speaker_notes', f"This is slide {i+1}")
                        audio_content = lesson_gen.generate_audio(speaker_notes)
                        if audio_content:
                            audio_files.append((f"slide_{i+1}.mp3", audio_content))
                    except Exception as e:
                        st.warning(f"Error generating audio for slide {i+1}: {str(e)}")
                        continue
                
                # Enhanced completion status
                if not MOVIEPY_AVAILABLE:
                    status_container.markdown("""
                    <div class="status-warning">
                        ⚠️ <strong>Video generation is not available in this environment.</strong><br>
                        PowerPoint and audio files are ready for download!
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    status_container.markdown("""
                    <div class="status-info">
                        ℹ️ <strong>Video generation would happen here if MoviePy was available.</strong><br>
                        All other materials are ready!
                    </div>
                    """, unsafe_allow_html=True)
                
                status_container.markdown("""
                <div class="status-success">
                    ✅ <strong>Generation complete!</strong><br>
                    Your professional lesson materials are ready for download.
                </div>
                """, unsafe_allow_html=True)
                
                st.session_state.pptx_buffer = pptx_buffer
                st.session_state.audio_files = audio_files
                st.session_state.video_path = None  # No video for now
                st.session_state.current_step = 5
                
                time.sleep(2)
                st.rerun()
            else:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #fef2f2, #fecaca); padding: 1.5rem; border-radius: 12px; border-left: 4px solid #ef4444;">
                    ❌ <strong>PowerPoint generation failed.</strong><br>
                    Please try again or go back to regenerate the slides.
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Step 5: Final Output
        elif st.session_state.current_step == 5:
            st.markdown("""
            <div class="status-success" style="text-align: center; padding: 2rem;">
                <h2 style="color: #065f46; font-family: 'Playfair Display', serif; margin-bottom: 1rem;">🎉 Your Lesson Materials Are Ready!</h2>
                <p style="font-size: 1.1rem;">Professional-quality educational content generated with AI</p>
            </div>
            """, unsafe_allow_html=True)
            
            data = st.session_state.lesson_data
            
            # Enhanced Summary with beautiful metrics
            st.markdown("<h3 style='color: #6366f1; font-family: Inter, sans-serif; text-align: center; margin: 2rem 0;'>📊 Lesson Summary</h3>", unsafe_allow_html=True)
            
            summary_cols = st.columns(4)
            
            with summary_cols[0]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(data['slides'])}</div>
                    <div class="metric-label">Slides Generated</div>
                </div>
                """, unsafe_allow_html=True)
            
            with summary_cols[1]:
                audio_count = len(st.session_state.audio_files) if hasattr(st.session_state, 'audio_files') else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{audio_count}</div>
                    <div class="metric-label">Audio Files</div>
                </div>
                """, unsafe_allow_html=True)
            
            with summary_cols[2]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{data['duration']}</div>
                    <div class="metric-label">Minutes Duration</div>
                </div>
                """, unsafe_allow_html=True)
            
            with summary_cols[3]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{data['grade_level']}</div>
                    <div class="metric-label">Target Level</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Enhanced Download section
            st.markdown("<h3 style='color: #14b8a6; font-family: Inter, sans-serif; text-align: center; margin: 2rem 0;'>📥 Download Your Materials</h3>", unsafe_allow_html=True)
            
            download_cols = st.columns(3)
            
            with download_cols[0]:
                if hasattr(st.session_state, 'pptx_buffer') and st.session_state.pptx_buffer:
                    st.download_button(
                        label="📄 Download PowerPoint",
                        data=st.session_state.pptx_buffer.getvalue(),
                        file_name=f"{data['title']}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        help="Editable PowerPoint presentation"
                    )
            
            with download_cols[1]:
                if hasattr(st.session_state, 'audio_files') and st.session_state.audio_files:
                    # Create ZIP file with all audio files
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for filename, audio_content in st.session_state.audio_files:
                            zip_file.writestr(filename, audio_content)
                    
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label="🔊 Download Audio Files",
                        data=zip_buffer.getvalue(),
                        file_name=f"{data['title']}_audio.zip",
                        mime="application/zip",
                        help="All narration audio files in ZIP format"
                    )
            
            with download_cols[2]:
                st.markdown("""
                <div style="background: linear-gradient(135deg, #f1f5f9, #e2e8f0); padding: 1rem; border-radius: 12px; text-align: center; height: 60px; display: flex; align-items: center; justify-content: center;">
                    <span style="color: #64748b; font-weight: 500;">🎬 Video: Not Available</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Individual audio files section with enhanced styling
            if hasattr(st.session_state, 'audio_files') and st.session_state.audio_files:
                with st.expander("🎵 Individual Audio Files", expanded=False):
                    st.markdown("<p style='text-align: center; color: #6b7280; margin-bottom: 1rem;'>Download individual slide narrations:</p>", unsafe_allow_html=True)
                    
                    audio_cols = st.columns(3)
                    for i, (filename, audio_content) in enumerate(st.session_state.audio_files):
                        col_idx = i % 3
                        with audio_cols[col_idx]:
                            st.download_button(
                                label=f"🔊 {filename}",
                                data=audio_content,
                                file_name=filename,
                                mime="audio/mpeg",
                                key=f"audio_{i}"
                            )
            
            # Enhanced status messages
            st.markdown("""
            <div class="status-success">
                🎉 <strong>PowerPoint and audio files have been generated successfully!</strong><br>
                Your professional lesson materials are ready to use in the classroom.
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="status-info">
                📹 <strong>Pro Tip:</strong> To create a video, combine the PowerPoint slides with audio files using video editing software like Camtasia, Adobe Premiere, or free alternatives like DaVinci Resolve.
            </div>
            """, unsafe_allow_html=True)
            
            # Enhanced action buttons
            action_cols = st.columns(2)
            
            with action_cols[0]:
                if st.button("🔄 Create Another Lesson", type="primary"):
                    # Reset session state
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            
            with action_cols[1]:
                if st.button("📧 Share Feedback", type="secondary"):
                    st.markdown("""
                    <div class="status-info">
                        💌 <strong>Love the app? Have suggestions?</strong><br>
                        We'd love to hear from you! Your feedback helps us improve.
                    </div>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
