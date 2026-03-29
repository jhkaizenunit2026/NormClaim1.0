const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(email: string): string | null {
  const t = email.trim();
  if (!t) return "Email is required.";
  if (!EMAIL_RE.test(t)) return "Enter a valid email address.";
  return null;
}

export function validatePassword(password: string, min = 6): string | null {
  if (!password) return "Password is required.";
  if (password.length < min) return `Password must be at least ${min} characters.`;
  return null;
}

export function validateName(name: string): string | null {
  const t = name.trim();
  if (!t) return "Name is required.";
  if (t.length < 2) return "Name is too short.";
  return null;
}
