import streamlit as st
import bs4
from io import StringIO

st.set_page_config(page_title="HTML Parser", page_icon="🔍", layout="wide")

def find_element(soup, tag=None, class_=None, id_=None, keyword=None):
    """
    Finds the first element matching tag, class, or id.
    Returns element info: full HTML, text, attributes.
    If 'keyword' is provided and found anywhere, returns True.
    """
    if tag:
        elem = soup.find(tag)
    elif class_:
        elem = soup.find(class_=class_)
    elif id_:
        elem = soup.find(id=id_)
    else:
        return None, "Please provide a tag, class, or id."

    if elem:
        result = {
            "html": elem.prettify(),
            "text": elem.get_text(strip=True),
            "attributes": dict(elem.attrs),
            "keyword_found": False
        }
        
        # Keyword search in text and attributes
        if keyword:
            content = elem.get_text() + " " + " ".join(str(v) for v in elem.attrs.values())
            if keyword in content:
                result["keyword_found"] = True
        
        return elem, result
    else:
        return None, "No element found with the specified criteria."

def main():
    st.title("🔍 HTML Element Parser")
    st.markdown("Upload an HTML file and search for specific elements")
    
    # File upload
    uploaded_file = st.file_uploader("Upload HTML file", type=['html', 'htm'])
    
    # Or paste HTML
    html_text = st.text_area("Or paste HTML content here:", height=150)
    
    soup = None
    
    if uploaded_file is not None:
        # Read the uploaded file
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        html_content = stringio.read()
        soup = bs4.BeautifulSoup(html_content, "html.parser")
        st.success("✅ HTML file loaded successfully!")
    elif html_text:
        soup = bs4.BeautifulSoup(html_text, "html.parser")
        st.success("✅ HTML content parsed successfully!")
    
    if soup:
        st.divider()
        st.subheader("🔎 Search for Elements")
        
        # Search options
        col1, col2 = st.columns(2)
        
        with col1:
            search_by = st.radio(
                "Search by:",
                ["Tag", "Class", "ID"],
                horizontal=True
            )
        
        with col2:
            keyword = st.text_input("🔑 Keyword to search (optional):", placeholder="e.g., Anlagenmechaniker")
        
        if search_by == "Tag":
            search_value = st.text_input("Tag name:", placeholder="e.g., div, span, a")
            search_params = {"tag": search_value if search_value else None}
        elif search_by == "Class":
            search_value = st.text_input("Class name:", placeholder="e.g., col-xs-6 col-sm-6")
            search_params = {"class_": search_value if search_value else None}
        else:  # ID
            search_value = st.text_input("ID:", placeholder="e.g., main-content")
            search_params = {"id_": search_value if search_value else None}
        
        if st.button("🔍 Search", type="primary"):
            if search_value:
                with st.spinner("Searching..."):
                    elem, result = find_element(soup, **search_params, keyword=keyword)
                    
                    if elem:
                        if isinstance(result, dict):
                            # Show keyword match
                            if keyword and result["keyword_found"]:
                                st.success("🎉 Yuhuu! Keyword found in element!")
                            
                            # Display results in tabs
                            tab1, tab2, tab3 = st.tabs(["📄 HTML", "📝 Text Content", "🏷️ Attributes"])
                            
                            with tab1:
                                st.code(result["html"], language="html")
                            
                            with tab2:
                                st.text_area("Text content:", result["text"], height=200)
                            
                            with tab3:
                                if result["attributes"]:
                                    for attr, value in result["attributes"].items():
                                        st.write(f"**{attr}:** {value}")
                                else:
                                    st.info("No attributes found")
                    else:
                        st.error(result)  # Error message
            else:
                st.warning("⚠️ Please enter a search value")
    else:
        st.info("👆 Please upload an HTML file or paste HTML content to get started")
        
        # Example section
        with st.expander("💡 Example Usage"):
            st.markdown("""
            **How to use this tool:**
            
            1. Upload an HTML file or paste HTML content
            2. Choose search method (Tag, Class, or ID)
            3. Enter the search value
            4. Optionally add a keyword to search within the element
            5. Click Search to find the element
            
            **Example searches:**
            - **Tag:** `div`, `span`, `a`, `p`
            - **Class:** `col-xs-6 col-sm-6 col-md-6 col-lg-6`
            - **ID:** `main-content`, `header`
            - **Keyword:** `Anlagenmechaniker` (will highlight if found)
            """)

if __name__ == "__main__":
    main()