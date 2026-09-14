import os

# Guarantee all tests execute in zero-cost, offline dress rehearsal mode
os.environ["AUDITLANE_DRESS_REHEARSAL"] = "true"
