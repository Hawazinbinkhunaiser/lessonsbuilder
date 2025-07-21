# app.py - Clean version without progress bar issues
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

# Custom CSS for better appearance
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
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
        """Create PowerPoint presentation"""
        try:
            if not slides_data or not isinstance(slides_data, list):
                st.error("Invalid slide data provided")
                return None
                
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
                try:
                    bullet_layout = prs.slide_layouts[1]
                    slide = prs.slides.add_slide(bullet_layout)
                    
                    title_shape = slide.shapes.title
                    title_shape.text = slide_data.get('title', 'Untitled Slide')
                    
                    content_shape = slide.placeholders[1]
                    text_frame = content_shape.text_frame
                    text_frame.clear()
                    
                    content_points = slide_data.get('content', [])
                    if isinstance(content_points, list):
                        for point in content_points:
                            if point and isinstance(point, str):
                                p = text_frame.add_paragraph()
                                p.text = str(point)
                                p.level = 0
                    else:
                        p = text_frame.add_paragraph()
                        p.text = str(content_points)
                        p.level = 0
                        
                except Exception as slide_error:
                    st.warning(f"Error creating slide {slide_data.get('slide_number', 'unknown')}: {str(slide_error)}")
                    continue
            
            # Save to BytesIO
            pptx_buffer = io.BytesIO()
            prs.save(pptx_buffer)
            pptx_buffer.seek(0)
            
            return pptx_buffer
        except Exception as e:
            st.error(f"Error creating PowerPoint: {str(e)}")
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
                help="Get from: https://console.anthropic.com/"
            )
            elevenlabs_key = st.text_input(
                "ElevenLabs API Key", 
                type="password", 
                help="Get from: https://elevenlabs.io/"
            )
        
        if not claude_key or not elevenlabs_key:
            st.warning("⚠️ Please enter both API keys to continue")
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
    
    # Initialize lesson generator
    if claude_key and elevenlabs_key:
        lesson_gen = LessonGenerator(claude_key, elevenlabs_key)
    else:
        return
    
    # Main content area
    main_container = st.container()
    
    with main_container:
        # Step 1: Input Collection
        if st.session_state.current_step == 1:
            st.header("📝 Step 1: Lesson Setup")
            
            col1, col2 = st.columns(2)
            
            with col1:
                lesson_title = st.text_input("Lesson Title", placeholder="e.g., Introduction to Photosynthesis")
                subject = st.selectbox("Subject", ["Science", "Math", "History", "English", "Social Studies", "Other"])
                grade_level = st.selectbox("Grade Level", ["Elementary", "Middle School", "High School", "College"])
            
            with col2:
                duration = st.slider("Lesson Duration (minutes)", 10, 60, 30)
                objectives = st.text_area("Learning Objectives", placeholder="What should students learn?", height=150)
            
            st.subheader("📎 Upload Learning Material")
            uploaded_file = st.file_uploader("Choose a file", type=['txt'], help="Upload TXT files only")
            
            # Quick demo option
            demo_section = st.expander("🚀 Quick Demo")
            with demo_section:
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
                        with st.spinner("Creating demo lesson..."):
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
            
            # Process uploaded file
            if uploaded_file and lesson_title and objectives:
                if st.button("🚀 Analyze Content & Generate Facts", type="primary"):
                    with st.spinner("Processing your content..."):
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
            st.header("🔍 Step 2: Content Analysis & Review")
            
            data = st.session_state.lesson_data
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📚 Extracted Content Preview")
                st.text_area("Content", data['content'][:500] + "...", height=200, disabled=True)
                
            with col2:
                st.subheader("🎯 Interesting Facts Generated")
                st.markdown(data['facts'])
            
            st.subheader("📋 Lesson Overview")
            with st.expander("Review Lesson Details", expanded=True):
                st.write(f"**Title:** {data['title']}")
                st.write(f"**Subject:** {data['subject']}")
                st.write(f"**Grade Level:** {data['grade_level']}")
                st.write(f"**Duration:** {data['duration']} minutes")
                st.write(f"**Objectives:** {data['objectives']}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("⬅️ Back to Edit", type="secondary"):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col2:
                if st.button("🔄 Regenerate Facts", type="secondary"):
                    with st.spinner("Regenerating facts..."):
                        new_facts = lesson_gen.get_interesting_facts(data['title'], data['content'])
                        st.session_state.lesson_data['facts'] = new_facts
                        st.rerun()
            
            with col3:
                if st.button("✅ Create Lesson Outline", type="primary"):
                    with st.spinner("Creating lesson outline and slide content..."):
                        outline = lesson_gen.create_lesson_outline(data['objectives'], data['content'], data['facts'])
                        slides = lesson_gen.generate_slide_content(outline, data['objectives'])
                        
                        st.session_state.lesson_data['outline'] = outline
                        st.session_state.lesson_data['slides'] = slides
                        st.session_state.current_step = 3
                        st.rerun()
        
        # Step 3: Review and Approve
        elif st.session_state.current_step == 3:
            st.header("👀 Step 3: Review & Approve Content")
            
            data = st.session_state.lesson_data
            
            st.subheader("📋 Lesson Outline")
            with st.expander("View Complete Outline", expanded=True):
                st.markdown(data['outline'])
            
            st.subheader("🖼️ Slide Previews")
            
            if 'slides' in data and data['slides']:
                for slide in data['slides']:
                    with st.expander(f"Slide {slide['slide_number']}: {slide['title']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Content:**")
                            for point in slide['content']:
                                st.write(f"• {point}")
                            st.write(f"**Suggested Image:** {slide['image_description']}")
                        
                        with col2:
                            st.write("**Speaker Notes:**")
                            st.write(slide['speaker_notes'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("⬅️ Back to Analysis", type="secondary"):
                    st.session_state.current_step = 2
                    st.rerun()
            
            with col2:
                if st.button("🔄 Regenerate Slides", type="secondary"):
                    with st.spinner("Regenerating slide content..."):
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
            st.header("🎬 Step 4: Generate Presentation Materials")
            
            data = st.session_state.lesson_data
            
            if not st.session_state.slides_approved:
                st.error("Please approve the content first")
                return
            
            # Status tracking without progress bar
            status_container = st.empty()
            
            # Generate PowerPoint
            status_container.info("🔄 Creating PowerPoint presentation...")
            try:
                pptx_buffer = lesson_gen.create_powerpoint(data['slides'], data['title'])
            except Exception as e:
                st.error(f"Error creating PowerPoint: {str(e)}")
                pptx_buffer = None
            
            if pptx_buffer:
                status_container.info("🔄 Generating audio narration...")
                
                audio_files = []
                for i, slide in enumerate(data['slides']):
                    status_container.info(f"🔄 Generating audio for slide {i+1} of {len(data['slides'])}...")
                    try:
                        speaker_notes = slide.get('speaker_notes', f"This is slide {i+1}")
                        audio_content = lesson_gen.generate_audio(speaker_notes)
                        if audio_content:
                            audio_files.append((f"slide_{i+1}.mp3", audio_content))
                    except Exception as e:
                        st.warning(f"Error generating audio for slide {i+1}: {str(e)}")
                        continue
                
                # Note about video generation
                if not MOVIEPY_AVAILABLE:
                    status_container.warning("⚠️ Video generation is not available in this environment. PowerPoint and audio files are ready!")
                else:
                    status_container.info("ℹ️ Video generation would happen here if MoviePy was available.")
                
                status_container.success("✅ Generation complete!")
                
                st.session_state.pptx_buffer = pptx_buffer
                st.session_state.audio_files = audio_files
                st.session_state.video_path = None  # No video for now
                st.session_state.current_step = 5
                
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ PowerPoint generation failed. Please try again.")
                st.info("💡 Please go back and regenerate the slides.")
        
        # Step 5: Final Output
        elif st.session_state.current_step == 5:
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
                    st.metric("Title", data['title'])
                    st.metric("Subject", data['subject'])
                    st.metric("Grade Level", data['grade_level'])
                with col2:
                    st.metric("Slides Generated", len(data['slides']))
                    if hasattr(st.session_state, 'audio_files'):
                        st.metric("Audio Files", len(st.session_state.audio_files))
                    st.metric("Duration", f"{data['duration']} minutes")
            
            # Download section
            st.subheader("📥 Download Your Materials")
            
            # Main download buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if hasattr(st.session_state, 'pptx_buffer') and st.session_state.pptx_buffer:
                    st.download_button(
                        label="📄 Download PowerPoint",
                        data=st.session_state.pptx_buffer.getvalue(),
                        file_name=f"{data['title']}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        help="Editable PowerPoint presentation"
                    )
            
            with col2:
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
            
            with col3:
                st.info("🎬 Video generation not available in this environment")
            
            # Individual audio files section
            if hasattr(st.session_state, 'audio_files') and st.session_state.audio_files:
                with st.expander("🎵 Individual Audio Files"):
                    st.write("Download individual slide narrations:")
                    cols = st.columns(3)
                    for i, (filename, audio_content) in enumerate(st.session_state.audio_files):
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
            st.success("🎉 PowerPoint and audio files have been generated successfully!")
            st.info("📹 To create a video, combine the PowerPoint slides with audio files using video editing software")
            
            # Action buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Create Another Lesson", type="primary"):
                    # Reset session state
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
            
            with col2:
                if st.button("📧 Share Feedback", type="secondary"):
                    st.info("💌 Love the app? Have suggestions? Let us know!")

if __name__ == "__main__":
    main()
