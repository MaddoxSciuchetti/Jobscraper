import streamlit as st
import pandas as pd

# Initialize session state if not exists
if 'jobs' not in st.session_state:
    st.session_state.jobs = []

# Create a simple UI
st.title("🔍 Job Data Checker")

if not st.session_state.jobs:
    st.warning("No job data found in the current session.")
    st.info("Please run the Job Scraper first to collect job data.")
else:
    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.jobs)
    
    # Check for Anlagenmechaniker jobs
    anlagen_jobs = df[df['title'].str.contains('anlagenmechaniker', case=False, na=False)]
    
    st.subheader("🔍 Anlagenmechaniker Jobs Found")
    if len(anlagen_jobs) > 0:
        st.success(f"✅ Found {len(anlagen_jobs)} Anlagenmechaniker jobs!")
        
        # Check for phone numbers
        anlagen_jobs_with_phone = anlagen_jobs[anlagen_jobs['phone'] != 'N/A']
        
        if len(anlagen_jobs_with_phone) > 0:
            st.success(f"✅ {len(anlagen_jobs_with_phone)} jobs have phone numbers!")
            st.dataframe(anlagen_jobs_with_phone[['title', 'company', 'phone', 'url']])
            
            # Save results to CSV
            csv = anlagen_jobs_with_phone.to_csv(index=False)
            st.download_button(
                "💾 Download Anlagenmechaniker Jobs with Phone Numbers",
                data=csv,
                file_name="anlagenmechaniker_jobs.csv",
                mime="text/csv"
            )
        else:
            st.warning("ℹ️ No phone numbers found for Anlagenmechaniker jobs.")
            st.dataframe(anlagen_jobs[['title', 'company', 'phone', 'url']])
    else:
        st.warning("⚠️ No Anlagenmechaniker jobs found in the current session data.")
    
    # Show all jobs for reference
    st.subheader("📋 All Jobs in Session")
    st.dataframe(df[['title', 'company', 'phone']])
