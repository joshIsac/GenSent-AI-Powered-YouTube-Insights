import streamlit as st
import login_database as login_database  # Import the database functions

def main():
    login_database.init_db()  # Initialize database (Run once)

    st.sidebar.title("🔑 User Authentication")

    if not st.session_state.authenticated:
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")

        if st.sidebar.button("Login"):
            if login_database.authenticate(username, password):
                st.sidebar.success(f"✅ Welcome, {username}!")
                st.session_state.authenticated = True
                st.session_state.username = username  # Store username
                st.session_state.page = "home"
                

            else:
                st.sidebar.error("❌ Invalid credentials!")
                st.session.state.authenticated = False

        if st.sidebar.button("Register"):
            if login_database.register_user(username, password):
                st.sidebar.success("✅ User registered successfully!")
            else:
                st.sidebar.warning("⚠️ Username already exists!")

    else:
        st.sidebar.success("🎉 You are logged in!")


    if st.sidebar.button("Logout"):
        if login_database.logout_user():
            st.sidebar.success("🔒 Logged out successfully!") 

if __name__ == "__main__":
    main()
