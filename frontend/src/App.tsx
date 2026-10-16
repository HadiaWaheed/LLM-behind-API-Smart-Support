
import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";
import "./App.css";

const API =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const TOKEN_KEY = "supportpilot_token";

type User = {
  id?: number;
  name?: string;
  email: string;
  role?: string;
};

type Message = {
  id?: number;
  sender_role?: string;
  role?: string;
  sender?: string;
  content?: string;
  message?: string;
  created_at?: string;
};

type Ticket = {
  id: number;
  ticket_id?: number;
  subject?: string;
  title?: string;
  status?: string;
  category?: string;
  urgency?: string;
  confidence?: number | null;
  suggested_team?: string;
  escalated?: boolean;
  created_at?: string;
  messages?: Message[];
  answer?: string;
  ai_answer?: string;
  response?: string;
};

type Feedback = "helpful" | "not-helpful" | null;

async function apiRequest(
  path: string,
  init: RequestInit = {},
  token?: string | null,
) {
  const headers = new Headers(init.headers);

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;

  try {
    response = await fetch(`${API}${path}`, {
      ...init,
      headers,
    });
  } catch {
    throw new Error(
      "Backend se connection nahi ho raha. Check karo ke FastAPI server running hai.",
    );
  }

  const text = await response.text();
  let data: any = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : `Request failed (${response.status}).`;

    const error = new Error(detail) as Error & {
      status?: number;
    };

    error.status = response.status;
    throw error;
  }

  return data;
}

function readUser(payload: any, emailFallback = ""): User {
  const source = payload?.user ?? payload;

  return {
    id: source?.id,
    name: source?.name || "",
    email: source?.email || emailFallback,
    role: source?.role || "customer",
  };
}

function answerFrom(ticket: Ticket | any): string {
  const messages: Message[] = Array.isArray(ticket?.messages)
    ? ticket.messages
    : [];

  const assistantMessage = [...messages]
    .reverse()
    .find((message) => {
      const role = String(
        message.sender_role ?? message.role ?? message.sender ?? "",
      ).toLowerCase();

      return ["assistant", "ai", "bot"].includes(role);
    });

  const messageContent =
    assistantMessage?.content ?? assistantMessage?.message;

  if (typeof messageContent === "string" && messageContent.trim()) {
    return messageContent.trim();
  }

  const directAnswer =
    ticket?.answer ?? ticket?.ai_answer ?? ticket?.response;

  if (typeof directAnswer === "string" && directAnswer.trim()) {
    return directAnswer.trim();
  }

  return "";
}

function formatDate(value?: string) {
  if (!value) return "";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "";

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function titleFromTicket(ticket: Ticket) {
  return (
    ticket.subject ||
    ticket.title ||
    ticket.messages?.find((message) => {
      const role = String(
        message.sender_role ?? message.role ?? message.sender ?? "",
      ).toLowerCase();

      return role === "customer";
    })?.content ||
    ticket.messages?.find((message) => {
      const role = String(
        message.sender_role ?? message.role ?? message.sender ?? "",
      ).toLowerCase();

      return role === "customer";
    })?.message ||
    `Conversation #${ticket.id}`
  );
}

function humanize(value?: string | null) {
  if (!value) return "Not available";

  return value
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function App() {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem(TOKEN_KEY),
  );

  const [user, setUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [currentTicket, setCurrentTicket] = useState<Ticket | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);

  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [initializing, setInitializing] = useState(Boolean(token));

  const [error, setError] = useState("");
  const [authError, setAuthError] = useState("");
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [page, setPage] = useState<"home" | "history" | "help">("home");

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setTickets([]);
    setCurrentTicket(null);
    setQuestion("");
    setAnswer("");
    setFeedback(null);
    setError("");
    setAuthError("");
    setInitializing(false);
  }, []);

  const loadHistory = useCallback(async (activeToken: string) => {
    const data = await apiRequest(
      "/support/tickets",
      {},
      activeToken,
    );

    const list = Array.isArray(data)
      ? data
      : data?.tickets ?? data?.items ?? data?.data ?? [];

    setTickets(Array.isArray(list) ? list : []);
  }, []);

  useEffect(() => {
    if (!token) {
      setInitializing(false);
      return;
    }

    let cancelled = false;

    async function restoreSession() {
      try {
        const payload = await apiRequest("/auth/me", {}, token);

        if (cancelled) return;

        const restoredUser = readUser(payload);

        if (restoredUser.role !== "customer") {
          throw new Error("This account is not enabled for customer access.");
        }

        setUser(restoredUser);

        try {
          await loadHistory(token!);
        } catch (historyError) {
          if (!cancelled) {
            setError(
              historyError instanceof Error
                ? historyError.message
                : "Could not load conversation history.",
            );
          }
        }
      } catch {
        if (!cancelled) {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) setInitializing(false);
      }
    }

    void restoreSession();

    return () => {
      cancelled = true;
    };
  }, [token, loadHistory]);

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");
    setAuthLoading(true);

    try {
      const normalizedEmail = email.trim().toLowerCase();

      if (authMode === "signup") {
        await apiRequest("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            name: name.trim(),
            email: normalizedEmail,
            password,
          }),
        });
      }

      const loginData = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: normalizedEmail,
          password,
        }),
      });

      if (!loginData?.access_token) {
        throw new Error("Login succeeded but no access token was returned.");
      }

      if (
        loginData.role &&
        String(loginData.role).toLowerCase() !== "customer"
      ) {
        throw new Error("This application is for customer accounts only.");
      }

      localStorage.setItem(TOKEN_KEY, loginData.access_token);
      setToken(loginData.access_token);

      const currentUser = await apiRequest(
        "/auth/me",
        {},
        loginData.access_token,
      );

      const restoredUser = readUser(currentUser, normalizedEmail);

      if (restoredUser.role !== "customer") {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        throw new Error("This application is for customer accounts only.");
      }

      setUser(restoredUser);
      setPassword("");
      setPage("home");
      setError("");

      try {
        await loadHistory(loginData.access_token);
      } catch {
        setTickets([]);
      }
    } catch (authException) {
      setAuthError(
        authException instanceof Error
          ? authException.message
          : "Authentication failed. Please try again.",
      );
    } finally {
      setAuthLoading(false);
    }
  }

  function startNewChat() {
    setQuestion("");
    setAnswer("");
    setCurrentTicket(null);
    setFeedback(null);
    setError("");
    setPage("home");
  }

  async function askAI(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !question.trim() || loading) return;

    const customerQuestion = question.trim();

    setLoading(true);
    setError("");
    setAnswer("");
    setFeedback(null);

    try {
      const result = await apiRequest(
        "/support/tickets",
        {
          method: "POST",
          body: JSON.stringify({
            message: customerQuestion,
          }),
        },
        token,
      );

      const ticket: Ticket = result?.ticket ?? result;

      // IMPORTANT: Attach messages before extracting the AI answer.
      const returnedMessages: Message[] = Array.isArray(result?.messages)
        ? result.messages
        : Array.isArray(ticket?.messages)
          ? ticket.messages
          : [];

      const completeTicket: Ticket = {
        ...ticket,
        messages: returnedMessages,
      };

      const aiAnswer = answerFrom(completeTicket);

      setCurrentTicket(completeTicket);
      setQuestion(customerQuestion);
      setAnswer(aiAnswer);
      setPage("home");

      // Show a useful message if the backend returned no AI answer.
      if (!aiAnswer) {
        setError(
          "The ticket was created, but the server did not return an AI answer. Please check the backend response and saved messages.",
        );
      }

      try {
        await loadHistory(token);
      } catch (historyError) {
        console.error("Could not refresh conversation history:", historyError);
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not get an AI response. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function openConversation(ticketId: number) {
    if (!token) return;

    setError("");
    setLoading(true);
    setFeedback(null);

    try {
      const result = await apiRequest(
        `/support/tickets/${ticketId}`,
        {},
        token,
      );

      const ticket: Ticket = result?.ticket ?? result;

      const returnedMessages: Message[] = Array.isArray(result?.messages)
        ? result.messages
        : Array.isArray(ticket?.messages)
          ? ticket.messages
          : [];

      const completeTicket: Ticket = {
        ...ticket,
        messages: returnedMessages,
      };

      setCurrentTicket(completeTicket);

      const customerMessage = completeTicket.messages?.find((message) => {
        const role = String(
          message.sender_role ?? message.role ?? message.sender ?? "",
        ).toLowerCase();

        return role === "customer";
      });

      setQuestion(
        customerMessage?.content ||
          customerMessage?.message ||
          completeTicket.subject ||
          completeTicket.title ||
          "",
      );

      const aiAnswer = answerFrom(completeTicket);
      setAnswer(aiAnswer);

      if (!aiAnswer) {
        setError(
          "No AI answer was found in this conversation's saved messages.",
        );
      }

      setPage("home");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not open this conversation.",
      );
    } finally {
      setLoading(false);
    }
  }

  if (initializing) {
    return (
      <main className="auth-page">
        <div className="auth-card">
          <h2>SupportPilot AI</h2>
          <p>Restoring your session...</p>
        </div>
      </main>
    );
  }

  if (!token || !user) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <div className="brand-mark">S</div>

          <h1>SupportPilot AI</h1>
          <p className="muted">
            Your AI-powered customer support assistant.
          </p>

          <div className="auth-tabs">
            <button
              type="button"
              className={authMode === "login" ? "active" : ""}
              onClick={() => {
                setAuthMode("login");
                setAuthError("");
              }}
            >
              Login
            </button>

            <button
              type="button"
              className={authMode === "signup" ? "active" : ""}
              onClick={() => {
                setAuthMode("signup");
                setAuthError("");
              }}
            >
              Create account
            </button>
          </div>

          <form onSubmit={handleAuth} className="auth-form">
            {authMode === "signup" && (
              <label>
                Full name
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Your name"
                  minLength={2}
                  maxLength={150}
                  autoComplete="name"
                  required
                />
              </label>
            )}

            <label>
              Email address
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 6 characters"
                minLength={6}
                maxLength={128}
                autoComplete={
                  authMode === "signup"
                    ? "new-password"
                    : "current-password"
                }
                required
              />
            </label>

            {authError && (
              <p className="error-message" role="alert">
                {authError}
              </p>
            )}

            <button
              type="submit"
              className="primary-button"
              disabled={authLoading}
            >
              {authLoading
                ? "Please wait..."
                : authMode === "login"
                  ? "Login to SupportPilot"
                  : "Create customer account"}
            </button>
          </form>

          <p className="auth-footer">
            Customer support, made simpler.
          </p>
        </section>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button
          type="button"
          className="brand"
          onClick={() => setPage("home")}
          aria-label="SupportPilot home"
        >
          <span className="brand-mark">S</span>
          <span>
            SupportPilot <strong>AI</strong>
          </span>
        </button>

        <nav className="top-nav" aria-label="Main navigation">
          <button
            type="button"
            className={page === "home" ? "nav-link active" : "nav-link"}
            onClick={() => setPage("home")}
          >
            Home
          </button>

          <button
            type="button"
            className={page === "history" ? "nav-link active" : "nav-link"}
            onClick={() => {
              setPage("history");
              setError("");
              void loadHistory(token).catch((loadError) =>
                setError(
                  loadError instanceof Error
                    ? loadError.message
                    : "Could not load conversations.",
                ),
              );
            }}
          >
            My Conversations
          </button>

          <button
            type="button"
            className={page === "help" ? "nav-link active" : "nav-link"}
            onClick={() => setPage("help")}
          >
            Help Center
          </button>
        </nav>

        <div className="user-menu">
          <div className="user-avatar">
            {(user.name || user.email).charAt(0).toUpperCase()}
          </div>

          <div className="user-details">
            <span>{user.name || "Customer"}</span>
            <small>{user.email}</small>
          </div>

          <button
            type="button"
            className="logout-button"
            onClick={logout}
          >
            Logout
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <button
            type="button"
            className="primary-button new-chat-button"
            onClick={startNewChat}
          >
            <span aria-hidden="true">＋</span> New Chat
          </button>

          <h3 className="sidebar-heading">RECENT CONVERSATIONS</h3>

          {tickets.length === 0 ? (
            <p className="empty-history">
              Your conversations will appear here.
            </p>
          ) : (
            <div className="conversation-list">
              {tickets.map((ticket) => (
                <button
                  type="button"
                  key={ticket.id}
                  className={
                    currentTicket?.id === ticket.id
                      ? "conversation-item selected"
                      : "conversation-item"
                  }
                  onClick={() => void openConversation(ticket.id)}
                >
                  <span className="conversation-title">
                    {titleFromTicket(ticket)}
                  </span>

                  <span className="conversation-meta">
                    #{ticket.id}
                    {ticket.created_at
                      ? ` · ${formatDate(ticket.created_at)}`
                      : ""}
                  </span>
                </button>
              ))}
            </div>
          )}

          <div className="sidebar-footer">
            <span className="status-dot" />
            AI Support Assistant
          </div>
        </aside>

        <main className="main-content">
          {page === "history" ? (
            <section className="content-section">
              <div className="page-heading">
                <span className="eyebrow">YOUR ACCOUNT</span>
                <h1>My Conversations</h1>
                <p>
                  View and continue your previous support conversations.
                </p>
              </div>

              {error && (
                <p className="error-message" role="alert">
                  {error}
                </p>
              )}

              {tickets.length === 0 ? (
                <div className="empty-state">
                  <h2>No conversations yet</h2>
                  <p>Start a new chat to ask your first question.</p>
                  <button
                    type="button"
                    className="primary-button"
                    onClick={startNewChat}
                  >
                    Start a conversation
                  </button>
                </div>
              ) : (
                <div className="history-grid">
                  {tickets.map((ticket) => (
                    <button
                      type="button"
                      key={ticket.id}
                      className="history-card"
                      onClick={() => void openConversation(ticket.id)}
                    >
                      <span className="history-card-icon">↗</span>
                      <strong>{titleFromTicket(ticket)}</strong>
                      <span>Conversation #{ticket.id}</span>
                      <small>{formatDate(ticket.created_at)}</small>
                    </button>
                  ))}
                </div>
              )}
            </section>
          ) : page === "help" ? (
            <section className="content-section">
              <div className="page-heading">
                <span className="eyebrow">SUPPORTPILOT</span>
                <h1>Help Center</h1>
                <p>Find help with your customer support questions.</p>
              </div>

              <div className="help-card">
                <h2>Ask the AI assistant</h2>
                <p>
                  Describe your question in the chat and SupportPilot will
                  use the available support information to help you.
                </p>
                <button
                  type="button"
                  className="primary-button"
                  onClick={startNewChat}
                >
                  Ask a question
                </button>
              </div>

              <div className="help-card">
                <h2>Need more assistance?</h2>
                <p>
                  If the available information does not answer your question,
                  the response may recommend contacting the support team.
                </p>
              </div>
            </section>
          ) : (
            <section className="chat-page">
              <div className="welcome-section">
                <span className="eyebrow">
                  CUSTOMER SUPPORT, SIMPLIFIED
                </span>
                <h1>
                  How can we help
                  <span className="heading-accent">
                    {user.name
                      ? `, ${user.name.split(" ")[0]}`
                      : " you"}
                    ?
                  </span>
                </h1>
                <p>
                  Ask a question and our AI assistant will help you find
                  the information you need.
                </p>
              </div>

              <form className="question-card" onSubmit={askAI}>
                <label htmlFor="customer-question">
                  What would you like help with?
                </label>

                <textarea
                  id="customer-question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Describe your question here..."
                  rows={4}
                  maxLength={2000}
                  disabled={loading}
                  required
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      !event.shiftKey &&
                      !event.nativeEvent.isComposing
                    ) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                />

                <div className="question-footer">
                  <span>{question.length}/2000 characters</span>

                  <button
                    type="submit"
                    className="primary-button ask-button"
                    disabled={loading || !question.trim()}
                  >
                    {loading ? "Thinking..." : "Ask AI"}
                    {!loading && <span aria-hidden="true"> →</span>}
                  </button>
                </div>
              </form>

              {error && (
                <div className="error-panel" role="alert">
                  <strong>Something went wrong</strong>
                  <p>{error}</p>
                  <button
                    type="button"
                    onClick={() => setError("")}
                  >
                    Dismiss
                  </button>
                </div>
              )}

              {loading && (
                <div className="answer-card loading-card" aria-live="polite">
                  <div className="assistant-icon">S</div>
                  <div>
                    <strong>SupportPilot is thinking...</strong>
                    <p>
                      Reviewing your question and preparing an answer.
                    </p>
                  </div>
                </div>
              )}

              {answer && currentTicket && !loading && (
                <article className="answer-card">
                  <div className="answer-header">
                    <div className="assistant-icon">S</div>
                    <div>
                      <h2>SupportPilot AI</h2>
                      <span className="answer-subtitle">
                        Response to your question
                      </span>
                    </div>
                    <span className="answer-badge">AI Response</span>
                  </div>

                  <div className="question-summary">
                    <span className="summary-label">YOUR QUESTION</span>
                    <p>
                      {question || titleFromTicket(currentTicket)}
                    </p>
                  </div>

                  <div className="answer-body">
                    <h3>Here's what I found</h3>
                    <p>{answer}</p>
                  </div>

                  <div className="ticket-details">
                    <div className="detail-item">
                      <span>Category</span>
                      <strong>
                        {humanize(currentTicket.category)}
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>Urgency</span>
                      <strong>
                        {humanize(currentTicket.urgency)}
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>Confidence</span>
                      <strong>
                        {typeof currentTicket.confidence === "number"
                          ? `${Math.round(
                              currentTicket.confidence <= 1
                                ? currentTicket.confidence * 100
                                : currentTicket.confidence,
                            )}%`
                          : "Not available"}
                      </strong>
                    </div>

                    <div className="detail-item">
                      <span>Suggested team</span>
                      <strong>
                        {humanize(currentTicket.suggested_team)}
                      </strong>
                    </div>
                  </div>

                  {currentTicket.escalated && (
                    <div className="escalation-note">
                      <strong>Additional support may be needed</strong>
                      <p>
                        This question may need further review. Please contact
                        your support team for assistance.
                      </p>
                    </div>
                  )}

                  <div className="feedback-section">
                    <div>
                      <strong>Was this answer helpful?</strong>
                      <p>
                        Your feedback helps us improve the experience.
                      </p>
                    </div>

                    <div className="feedback-actions">
                      <button
                        type="button"
                        className={
                          feedback === "helpful"
                            ? "feedback-button selected"
                            : "feedback-button"
                        }
                        onClick={() => setFeedback("helpful")}
                        aria-pressed={feedback === "helpful"}
                      >
                        👍 Yes
                      </button>

                      <button
                        type="button"
                        className={
                          feedback === "not-helpful"
                            ? "feedback-button selected"
                            : "feedback-button"
                        }
                        onClick={() => setFeedback("not-helpful")}
                        aria-pressed={feedback === "not-helpful"}
                      >
                        👎 No
                      </button>
                    </div>
                  </div>

                  {feedback && (
                    <p className="feedback-thanks" role="status">
                      {feedback === "helpful"
                        ? "Thanks! Glad this answer helped."
                        : "Thanks for your feedback. If you still need help, contact your support team."}
                    </p>
                  )}

                  <div className="answer-bottom">
                    <span>
                      Conversation #{currentTicket.id}
                    </span>

                    <button
                      type="button"
                      className="text-button"
                      onClick={startNewChat}
                    >
                      Ask another question →
                    </button>
                  </div>
                </article>
              )}

              {!answer && !loading && !error && (
                <div className="suggestion-section">
                  <h2>How can I help you today?</h2>
                  <p>
                    Ask about orders, billing, account access, refunds,
                    or any topic covered by your support knowledge base.
                  </p>
                </div>
              )}

              <p className="privacy-note">
                SupportPilot AI may make mistakes. Check important information
                with your support team when necessary.
              </p>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
