import {
  embeddingLabel,
  runtimeLabel,
  runtimeStartedLabel,
  runtimeVersionLabel,
} from "../utils/formatters.js";

export function StatusPanel({ status, error, busy, runtime }) {
  return (
    <aside className="status-panel">
      <div className={`orb ${busy ? "loading" : ""}`} />
      <div>
        <span>Runtime Status</span>
        <strong>{status}</strong>
        <p>
          {error ||
            `${runtimeLabel(runtime)}；${embeddingLabel(runtime)}；${runtimeVersionLabel(runtime)}；启动 ${runtimeStartedLabel(runtime)}。`}
        </p>
      </div>
    </aside>
  );
}

export function Metric({ label, value }) {
  return (
    <article className="metric">
      <small>{label}</small>
      <strong>{value}</strong>
    </article>
  );
}

export function StepCard({ number, title, tone, children }) {
  return (
    <article className={`step-card ${tone}`}>
      <div className="step-title">
        <span>{number}</span>
        <h2>{title}</h2>
      </div>
      {children}
    </article>
  );
}

export function Info({ label, value }) {
  return (
    <div className="info">
      <small>{label}</small>
      <code>{value}</code>
    </div>
  );
}

export function ResultBox({ title, subtitle, children }) {
  return (
    <div className="result-box">
      <div>
        <strong>{title}</strong>
        <small>{subtitle}</small>
      </div>
      <div className="result-content">{children}</div>
    </div>
  );
}

export function Progress({ value }) {
  return (
    <div className="progress" aria-label={`面试进度 ${value}%`}>
      <span style={{ width: `${value}%` }} />
    </div>
  );
}

export function TagRow({ tags }) {
  if (!tags?.length) return null;
  return (
    <div className="tag-row">
      {tags.map((tag) => (
        <span key={tag}>{tag}</span>
      ))}
    </div>
  );
}

export function FeedbackGroup({ title, children }) {
  return (
    <section className="feedback-group">
      <h3>{title}</h3>
      <div className="feedback-list">{children}</div>
    </section>
  );
}

export function FeedbackItem({ title, tags, children }) {
  return (
    <article className="feedback-item">
      <div className="feedback-item-head">
        <strong>{title}</strong>
        <TagRow tags={tags} />
      </div>
      <p>{children}</p>
    </article>
  );
}

export function MiniList({ items, empty }) {
  if (!items.length) return <Empty text={empty} />;
  return (
    <ul className="mini-list">
      {items.slice(0, 4).map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export function Empty({ text }) {
  return <div className="empty">{text}</div>;
}
