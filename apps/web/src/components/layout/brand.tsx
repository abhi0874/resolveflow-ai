export function Brand() {
  return (
    <a href="#top" className="brand" aria-label="ResolveFlow AI home">
      <span className="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 32 32" fill="none">
          <path
            d="M8 10h10a5 5 0 0 1 0 10h-4M8 10v13M8 10l6-5M8 10l6 5M24 22h-9"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span>
        ResolveFlow <span className="brand-ai">AI</span>
      </span>
    </a>
  );
}
