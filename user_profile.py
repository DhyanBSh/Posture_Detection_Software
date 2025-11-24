class UserProfile:
    def __init__(self, user_id, name, settings=None):
        self.user_id = user_id
        self.name = name
        # Safety: Ensure settings is a dict, even if None is passed
        self.settings = settings if settings is not None else {}
        self.current_session_id = None
    
    def get_setting(self, key, default=None):
        """Safely retrieve a setting value."""
        return self.settings.get(key, default)
    
    def update_setting(self, key, value):
        """Update a specific setting."""
        self.settings[key] = value
    
    def set_current_session(self, session_id):
        """Track the active session ID for database logging."""
        self.current_session_id = session_id
    
    def get_current_session(self):
        """Get the active session ID."""
        return self.current_session_id