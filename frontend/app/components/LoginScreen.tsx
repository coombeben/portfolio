"use client";

import { useState } from "react";
import { RateLimitError, useAuth } from "@/context/AuthContext";
import { UnauthorizedError } from "@/api/client";

export default function LoginScreen() {
  const { login } = useAuth();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(password);
      setPassword("");
    } catch (err) {
      if (err instanceof RateLimitError) {
        setError(err.message);
      } else if (err instanceof UnauthorizedError) {
        setError("Incorrect password.");
      } else {
        setError("Login failed. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="authScreen" role="dialog" aria-modal="true" aria-label="Login">
      <div className="authCard">
        <div className="authHeader">
          <div className="authTitle">Sign in</div>
          <div className="authSubtitle">Enter the password to continue.</div>
        </div>
        <form className="authForm" onSubmit={handleSubmit}>
          <label className="authLabel" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            className="authInput"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
          {error ? (
            <div className="authError" role="alert">
              {error}
            </div>
          ) : null}
          <button className="authButton" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
