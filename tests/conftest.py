import os

# Guarantee all tests execute in zero-cost, offline dress rehearsal mode
os.environ["AUDITLINE_DRESS_REHEARSAL"] = "true"
