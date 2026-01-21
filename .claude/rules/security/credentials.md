# Credential & Secret Security (ZERO TOLERANCE)

**Context:** A hardcoded API key in documentation caused real-world consequences. NEVER repeat this mistake.

## Absolute Rules

### 1. NEVER commit secrets to git

❌ **Prohibited:**
- API keys (Azure, AWS, Deepgram, OpenAI, Auth0, etc.)
- Passwords or tokens
- Private keys or certificates
- Database connection strings with credentials
- Any string that looks like: `sk-*`, `api_*`, `key=*`, `token=*`

### 2. NEVER put secrets in documentation

❌ **Prohibited:**
- README.md, CLAUDE.md, or any .md file
- Code comments
- Example files (use `<PLACEHOLDER>` instead)
- Curl examples with real keys

### 3. ALWAYS use environment variables

✅ **Required:**
- `.env` files (gitignored)
- `.env.example` with placeholders
- Secret managers (Auth0, GitHub Secrets, etc.)

## Claude Code Directive

When Claude sees ANY of these patterns, it MUST:
1. REFUSE to commit the file
2. WARN the user immediately
3. Suggest moving to .env

**Patterns to detect:**
```regex
export.*API.*KEY.*=.*["'][a-zA-Z0-9]{20,}["']
AZURE_API_KEY, OPENAI_API_KEY, DEEPGRAM_API_KEY, AWS_SECRET
Bearer [a-zA-Z0-9]{20,}
sk-[a-zA-Z0-9]{20,}
Any 32+ character hexadecimal or base64 string in quotes
```

Claude must **NEVER:**
- Commit files with hardcoded credentials
- Create "reference" or "example" files with real keys
- Suggest "just for testing" with real credentials
- Allow curl examples with actual API keys

Claude must **ALWAYS:**
- Use `.env.example` with `<YOUR_API_KEY_HERE>` placeholders
- Check staged files for credential patterns before commit
- Suggest `git-secrets` or pre-commit hooks for detection
- Recommend rotating any key that may have been exposed

## Recovery Procedure

If a secret is committed:

1. **IMMEDIATELY** rotate the exposed credential
2. Run: `git filter-repo --invert-paths --path <file> --force`
3. Force push: `git push --force --all`
4. Notify affected services (Azure, AWS, etc.)
5. Review access logs for unauthorized usage
