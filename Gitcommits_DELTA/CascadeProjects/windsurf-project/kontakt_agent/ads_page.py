import streamlit as st
import random
import string
import storage_utils as su  # NEW: read websites via helper


class AdStudioPage:
    def __init__(self):
        if "ad_code" not in st.session_state:
            st.session_state.ad_code = self._generate_code()
        if "uploaded_images" not in st.session_state:
            st.session_state.uploaded_images = []
        if "ad_texts" not in st.session_state:
            st.session_state.ad_texts = []
        if "leads" not in st.session_state:
            st.session_state.leads = []

    def _generate_code(self) -> str:
        letters = "".join(random.choice(string.ascii_uppercase) for _ in range(3))
        digits = "".join(random.choice(string.digits) for _ in range(4))
        return f"AD-{letters}{digits}"

    def _create_mock_leads(self):
        sample = [
            {"name": "M. Schneider", "topic": "Heizung warten", "phone": "+49 171 2345678"},
            {"name": "A. Meier", "topic": "Sanitär Reparatur", "phone": "030 1234567"},
            {"name": "C. Braun", "topic": "Badumbau", "phone": "+49 89 555555"}
        ]
        return sample

    def render(self):
        st.title("Ad Studio: Eigene Anzeigen & Leads")
        st.caption("Upload Fotos, erzeuge einen eindeutigen Code, schreibe eine Anzeige und simuliere eingehende Leads.")

        # 1) Fotos hochladen
        st.subheader("1) Fotos hochladen")
        files = st.file_uploader("Bestehende Fotos hochladen", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        if files:
            st.session_state.uploaded_images = files
            st.success(f"{len(files)} Bild(er) hochgeladen.")

        for f in st.session_state.uploaded_images:
            st.image(f, caption=f"Asset mit Code: {st.session_state.ad_code}", use_column_width=True)

        # 2) Einzigartigen Anzeigen-Code
        st.subheader("2) Einzigartigen Anzeigen-Code")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.text_input("Ad Code", value=st.session_state.ad_code, key="ad_code_input")
        with col2:
            if st.button("Neuen Code erzeugen"):
                st.session_state.ad_code = self._generate_code()
                st.success(f"Neuer Code: {st.session_state.ad_code}")

        # 3) Eigene Anzeige verfassen
        st.subheader("3) Eigene Anzeige verfassen (Text genügt)")
        ad_text = st.text_area("Anzeigentext", placeholder="Beschreibe kurz deine Dienstleistung/Angebot ...")
        if st.button("Anzeige speichern"):
            if ad_text.strip():
                st.session_state.ad_texts.append({"code": st.session_state.ad_code, "text": ad_text.strip()})
                if not st.session_state.leads:
                    st.session_state.leads = self._create_mock_leads()
                st.success("Anzeige gespeichert. Leads werden basierend auf deiner Anzeige simuliert.")
            else:
                st.warning("Bitte einen Text eingeben.")

        # 4) Inbox: Interessenten
        st.subheader("4) Inbox: Interessenten (Qualifizierte Leads)")
        if st.session_state.leads:
            names = [f"{i+1}. {lead['name']} - {lead['topic']}" for i, lead in enumerate(st.session_state.leads)]
            selected = st.selectbox("Eingehende Interessenten", names)
            idx = names.index(selected)
            lead = st.session_state.leads[idx]

            st.write(f"Name: {lead['name']}")
            st.write(f"Interesse: {lead['topic']}")
            st.write(f"Telefonnummer: {lead['phone']}")

            colA, colB, colC = st.columns([1, 1, 1])
            with colA:
                if st.button("Anrufen (simuliert)"):
                    st.info(f"Rufe {lead['name']} unter {lead['phone']} an ...")
            with colB:
                if st.button("Als qualifizierten Lead markieren"):
                    st.success(f"{lead['name']} ist nun ein qualifizierter Lead.")
            with colC:
                if st.button("Lead weiterreichen (an 'uns')"):
                    st.info("Lead wurde intern weitergegeben.")

            st.markdown("---")
            st.subheader("Handwerker kontaktieren (aus Web-Scraper)")
            websites = su.load_storage()
            if websites:
                target = st.selectbox("Handwerksbetrieb auswählen", websites)
            else:
                target = None
                st.warning("Keine gespeicherten Websites vorhanden. Bitte zuerst auf der 'Suche'-Seite scrapen.")

            msg = st.text_area("Nachricht/Angebot an den Handwerksbetrieb",
                               placeholder="Wir haben einen qualifizierten Lead für Sie ...")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Angebot senden"):
                    if target and msg.strip():
                        st.success(f"Angebot an {target} gesendet.")
                    else:
                        st.warning("Bitte Betrieb auswählen und eine Nachricht eingeben.")
            with col2:
                if st.button("Video-Call initiieren (simuliert)"):
                    st.info("Starte kurzen Video-Call ...")

            st.markdown("---")
            st.subheader("Vertrag & Vergütung")
            if st.button("Vertrag unterschrieben (simuliert)"):
                st.success("Vertrag unterschrieben. Vergütung ausgelöst.")
        else:
            st.info("Noch keine Leads vorhanden. Erstelle und speichere zuerst eine Anzeige.")
