import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def load_supabase_client(use_service_key: bool = False) -> Client:
"""Load Supabase client from Streamlit secrets.


If use_service_key is True it will use SUPABASE_KEY which may be a service_role key stored in secrets.
"""
url = st.secrets.get("SUPABASE_URL")
key = st.secrets.get("SUPABASE_KEY")
if not url or not key:
raise RuntimeError("Supabase credentials missing in st.secrets. Add SUPABASE_URL and SUPABASE_KEY.")
return create_client(url, key)


# single shared client
supabase = load_supabase_client()