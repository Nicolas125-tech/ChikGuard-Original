🎯 **What:**
The vulnerability fixed was a hardcoded superadmin password (`SUPERADMIN_PASSWORD = "chikguard_admin_secure"`) present in the `backend/scripts/create_superadmin.py` script. The hardcoded string was replaced by fetching the password from an environment variable (`os.environ.get("SUPERADMIN_PASSWORD")`), and the script was updated to error out if the variable is not set. In addition to this, the `main()` function's output was updated to mask the password string with asterisks when printing it to the terminal to prevent credential leaks in logs.

⚠️ **Risk:**
Leaving the superadmin password hardcoded in the codebase poses a critical security threat, particularly because it could be accidentally committed and exposed, leading to full unauthorized access and control over the application's system resources via the SuperAdmin account. Furthermore, having the plaintext password printed directly to the standard output during the script execution presents an unnecessary risk of the password leaking to server logs, terminal history, or CI/CD pipelines.

🛡️ **Solution:**
The script was updated to require the `SUPERADMIN_PASSWORD` via an environment variable, throwing a script exit condition (`sys.exit(1)`) if it wasn't supplied. The `SUPERADMIN_EMAIL` was updated as well to accept an environment fallback to offer flexibility and adhere to standard 12-factor application security practices. Output messages were also modified to mask the actual password value, printing `********` instead.
