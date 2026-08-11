"use client";

import { useState } from "react";

/**
 * The landing's game. You write a little about yourself, a small model on the
 * droplet reads it, and it hands you a name you may then edit.
 *
 * The only client component in this app, and it earns it: everything else here is
 * server-rendered HTML because it renders a database, but this is a conversation
 * with a stranger who has not decided to stay yet.
 */

type Named = { nickname: string; adjective: string; noun: string };

export default function NicknameGame() {
  const [text, setText] = useState("");
  const [name, setName] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState("");

  async function name_me() {
    if (!text.trim() || thinking) return;
    setThinking(true);
    setError("");
    try {
      const response = await fetch("/api/nickname", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const body = (await response.json()) as Named & { detail?: string };
      if (!response.ok) throw new Error(body.detail ?? "it did not answer");
      setName(body.nickname);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setThinking(false);
    }
  }

  return (
    <div className="game">
      <label htmlFor="about">Tell it something about you</label>
      <textarea
        id="about"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) name_me();
        }}
        placeholder="I fix old radios in my garage on sundays"
        maxLength={400}
        rows={3}
      />
      <div className="row">
        <button onClick={name_me} disabled={thinking || !text.trim()}>
          {thinking ? "reading you…" : name ? "name me again" : "name me"}
        </button>
        <span className="hint">⌘↵ · no Claude is called, the model runs on the droplet</span>
      </div>

      {error && <p className="wrong">{error}</p>}

      {name && (
        <div className="named">
          <span className="label">you are</span>
          <input
            id="nickname"
            name="nickname"
            value={name}
            onChange={(e) => setName(e.target.value)}
            spellCheck={false}
            aria-label="your nickname"
          />
          <span className="label">and you may edit that, it is your name</span>
        </div>
      )}
    </div>
  );
}
