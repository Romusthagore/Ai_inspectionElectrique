import streamlit as st

st.title("⚡ TEST APPLICATION")
st.success("✅ L'application fonctionne !")

observation = st.text_input("Saisissez une observation TEST:")
if observation:
    st.write(f"📝 Vous avez saisi: {observation}")
    st.info("🔍 L'analyse IA serait lancée ici...")

st.button("🚀 Bouton test")
