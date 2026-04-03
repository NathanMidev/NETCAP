sessions = {}

def is_authenticated(ip):
    return ip in sessions

def create_session(ip):
    sessions[ip] = True