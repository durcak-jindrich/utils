from typing import Dict, List
from pydantic import BaseModel, Field

class ChangedFile(BaseModel):
    filename: str = Field(..., description="The name and path of the file.")
    content: str = Field(..., description="The new content of the file.")
    diff: str = Field(..., description="The git diff format showing additions/deletions.")

class SamplePR(BaseModel):
    id: str = Field(..., description="Unique identifier for the sample PR.")
    title: str = Field(..., description="Title of the pull request.")
    description: str = Field(..., description="Description / description of changes.")
    files: List[ChangedFile] = Field(..., description="List of changed files in this PR.")

# 1. PR: Security Vulnerabilities
PR_SECURITY = SamplePR(
    id="pr_security",
    title="feat: Add user login and session store",
    description="Implements basic authentication and session storage for active users.",
    files=[
        ChangedFile(
            filename="auth/session.py",
            content="""import os
import redis

# Hardcoded production secret
SESSION_SECRET = "super-secret-key-128940-prod-abc"
REDIS_URL = "redis://admin:super_secret_redis_pass@prod-redis.internal:6379/0"

def get_redis_client():
    return redis.from_url(REDIS_URL)

def hash_session_id(session_id: str) -> str:
    # Weak cryptographic hash algorithm
    import hashlib
    return hashlib.md5(session_id.encode('utf-8')).hexdigest()
""",
            diff="""@@ -0,0 +1,14 @@
+import os
+import redis
+
+# Hardcoded production secret
++SESSION_SECRET = "super-secret-key-128940-prod-abc"
++REDIS_URL = "redis://admin:super_secret_redis_pass@prod-redis.internal:6379/0"
+
+def get_redis_client():
+    return redis.from_url(REDIS_URL)
+
+def hash_session_id(session_id: str) -> str:
+    # Weak cryptographic hash algorithm
+    import hashlib
+    return hashlib.md5(session_id.encode('utf-8')).hexdigest()"""
        ),
        ChangedFile(
            filename="auth/db.py",
            content="""import sqlite3

def find_user_by_name(username: str):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
""",
            diff="""@@ -0,0 +1,9 @@
+import sqlite3
+
+def find_user_by_name(username: str):
+    conn = sqlite3.connect("users.db")
+    cursor = conn.cursor()
+    # SQL injection vulnerability
+    +query = f"SELECT * FROM users WHERE username = '{username}'"
+    +cursor.execute(query)
+    return cursor.fetchone()"""
        )
    ]
)

# 2. PR: Architectural Violations
PR_ARCHITECTURE = SamplePR(
    id="pr_architecture",
    title="feat: Add user registration API endpoint",
    description="Registers a new user and sends welcome email.",
    files=[
        ChangedFile(
            filename="controllers/user_controller.py",
            content="""import psycopg2
from infrastructure.email.service import EmailSender

# Layering violation: Controller directly importing and handling database connection
# and executing raw queries rather than delegating to service/domain layer.
class UserController:
    def register_user(self, username, email, password):
        conn = psycopg2.connect("dbname=app user=postgres")
        cur = conn.cursor()
        
        # Directly writing SQL inside Controller
        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, password)
        )
        conn.commit()
        
        # Directly triggering side-effects from controller instead of event publishing
        email_sender = EmailSender()
        email_sender.send_welcome(email)
        
        cur.close()
        conn.close()
        return {"status": "success", "user": username}
""",
            diff="""@@ -0,0 +1,24 @@
+import psycopg2
+from infrastructure.email.service import EmailSender
+
+# Layering violation: Controller directly importing and handling database connection
+# and executing raw queries rather than delegating to service/domain layer.
++class UserController:
+    def register_user(self, username, email, password):
+        conn = psycopg2.connect("dbname=app user=postgres")
+        cur = conn.cursor()
+        
+        # Directly writing SQL inside Controller
+        cur.execute(
+            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
+            (username, email, password)
+        )
+        conn.commit()
+        
+        # Directly triggering side-effects from controller instead of event publishing
+        email_sender = EmailSender()
+        email_sender.send_welcome(email)
+        
+        cur.close()
+        conn.close()
+        return {"status": "success", "user": username}"""
        ),
        ChangedFile(
            filename="domain/user.py",
            content="""# Circular dependency violation
# Domain entity importing Controller to log actions
from controllers.user_controller import UserController

class User:
    def __init__(self, username, email):
        self.username = username
        self.email = email
        
    def log_creation(self):
        controller = UserController()
        print(f"Logging User {self.username} creation from domain using controller instance.")
""",
            diff="""@@ -0,0 +1,12 @@
+# Circular dependency violation
+# Domain entity importing Controller to log actions
++from controllers.user_controller import UserController
+
+class User:
+    def __init__(self, username, email):
+        self.username = username
+        self.email = email
+        
+    def log_creation(self):
+        controller = UserController()
+        print(f"Logging User {self.username} creation from domain using controller instance.")"""
        )
    ]
)

# 3. PR: Code Smells
PR_CODE_QUALITY = SamplePR(
    id="pr_code_quality",
    title="refactor: Update order processing logic",
    description="Updates order processing with tax, discount and notification logic.",
    files=[
        ChangedFile(
            filename="services/order_service.py",
            content="""class OrderService:
    # High cognitive complexity, long method, deeply nested blocks, and code duplication
    def process_order(self, order):
        if order is not None:
            if order.status == "PENDING":
                if order.items and len(order.items) > 0:
                    total = 0
                    for item in order.items:
                        if item.price > 0:
                            if item.category == "electronics":
                                total += item.price * 1.1 # 10% tax
                            elif item.category == "clothing":
                                total += item.price * 1.05 # 5% tax
                            else:
                                total += item.price
                        else:
                            print("Warning: Item price is zero or negative.")
                            
                    # Duplicate logic for discount calculation
                    if order.customer_type == "VIP":
                        total = total * 0.90 # 10% discount
                    elif order.customer_type == "ELITE":
                        total = total * 0.85 # 15% discount
                    else:
                        total = total
                        
                    # Duplicate logic for shipping calculation
                    if total > 100:
                        shipping = 0
                    else:
                        if order.shipping_method == "EXPRESS":
                            shipping = 15
                        else:
                            shipping = 5
                            
                    order.total = total + shipping
                    order.status = "PROCESSED"
                    
                    # Duplicate notification logic
                    if order.customer_email:
                        print(f"Sending receipt email to {order.customer_email} with total {order.total}")
                    if order.customer_phone:
                        print(f"Sending sms receipt to {order.customer_phone} with total {order.total}")
                else:
                    raise Exception("No items in order")
            else:
                raise Exception("Order is not in pending status")
        else:
            raise Exception("Order cannot be None")
""",
            diff="""@@ -0,0 +1,45 @@
+class OrderService:
+    # High cognitive complexity, long method, deeply nested blocks, and code duplication
+    def process_order(self, order):
+        if order is not None:
+            if order.status == "PENDING":
+                if order.items and len(order.items) > 0:
+                    total = 0
+                    for item in order.items:
+                        if item.price > 0:
+                            if item.category == "electronics":
+                                total += item.price * 1.1 # 10% tax
+                            elif item.category == "clothing":
+                                total += item.price * 1.05 # 5% tax
+                            else:
+                                total += item.price
+                        else:
+                            print("Warning: Item price is zero or negative.")
+                            
+                    # Duplicate logic for discount calculation
+                    if order.customer_type == "VIP":
+                        total = total * 0.90 # 10% discount
+                    elif order.customer_type == "ELITE":
+                        total = total * 0.85 # 15% discount
+                    else:
+                        total = total
+                        
+                    # Duplicate logic for shipping calculation
+                    if total > 100:
+                        shipping = 0
+                    else:
+                        if order.shipping_method == "EXPRESS":
+                            shipping = 15
+                        else:
+                            shipping = 5
+                            
+                    order.total = total + shipping
+                    order.status = "PROCESSED"
+                    
+                    # Duplicate notification logic
+                    if order.customer_email:
+                        print(f"Sending receipt email to {order.customer_email} with total {order.total}")
+                    if order.customer_phone:
+                        print(f"Sending sms receipt to {order.customer_phone} with total {order.total}")
+                else:
+                    raise Exception("No items in order")"""
        )
    ]
)

# 4. PR: Documentation Gaps
PR_DOCUMENTATION = SamplePR(
    id="pr_documentation",
    title="feat: Add support for regional taxation API",
    description="Exposes API for calculating taxes across regions. Note: missing README updates and public API comments.",
    files=[
        ChangedFile(
            filename="tax/calculator.py",
            content="""# Public API class containing tax calculations
# No docstrings, no explanations of variables, no parameter descriptions.
class TaxCalculator:
    def __init__(self, base_rate, adjustments):
        self.base_rate = base_rate
        self.adjustments = adjustments

    def calculate(self, amount, region, is_exempt=False):
        if is_exempt:
            return 0
        rate = self.base_rate
        if region in self.adjustments:
            rate += self.adjustments[region]
        return amount * rate
""",
            diff="""@@ -0,0 +1,14 @@
+# Public API class containing tax calculations
+# No docstrings, no explanations of variables, no parameter descriptions.
++class TaxCalculator:
+    def __init__(self, base_rate, adjustments):
+        self.base_rate = base_rate
+        self.adjustments = adjustments
+
+    def calculate(self, amount, region, is_exempt=False):
+        if is_exempt:
+            return 0
+        rate = self.base_rate
+        if region in self.adjustments:
+            rate += self.adjustments[region]
+        return amount * rate"""
        )
    ]
)

# 5. PR: Clean Pull Request (No major issues)
PR_CLEAN = SamplePR(
    id="pr_clean",
    title="feat: Implement basic math helper library",
    description="Provides basic mathematical helper functions (addition, multiplication) with full type hints, docstrings, and error handling.",
    files=[
        ChangedFile(
            filename="math_utils/helpers.py",
            content="""\"\"\"Math helpers for simple arithmetic.

Provides safe operations with error checking.
\"\"\"
from typing import Union

def safe_divide(numerator: Union[int, float], denominator: Union[int, float]) -> float:
    \"\"\"Divide two numbers safely, raising ValueError if denominator is zero.

    Args:
        numerator: The dividend.
        denominator: The divisor.

    Returns:
        The result of numerator / denominator.

    Raises:
        ValueError: If denominator is zero.
    \"\"\"
    if denominator == 0:
        raise ValueError("Denominator cannot be zero.")
    return float(numerator) / denominator
""",
            diff="""@@ -0,0 +1,21 @@
+\"\"\"Math helpers for simple arithmetic.
+
+Provides safe operations with error checking.
+\"\"\"
+from typing import Union
+
+def safe_divide(numerator: Union[int, float], denominator: Union[int, float]) -> float:
+    \"\"\"Divide two numbers safely, raising ValueError if denominator is zero.
+
+    Args:
+        numerator: The dividend.
+        denominator: The divisor.
+
+    Returns:
+        The result of numerator / denominator.
+
+    Raises:
+        ValueError: If denominator is zero.
+    \"\"\"
+    if denominator == 0:
+        raise ValueError("Denominator cannot be zero.")
+    return float(numerator) / denominator"""
        )
    ]
)

ALL_SAMPLES = [PR_SECURITY, PR_ARCHITECTURE, PR_CODE_QUALITY, PR_DOCUMENTATION, PR_CLEAN]
