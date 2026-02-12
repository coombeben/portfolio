export function Header () {
  return <header className="appHeader">
    <div className="appHeader__brand">
      <div className="appHeader__logo" aria-hidden="true">
        BC
      </div>
      <div>
        <div className="appHeader__name">Ben Coombe</div>
        <div className="appHeader__tagline">Interactive Portfolio Chat</div>
      </div>
    </div>
    <a
      className="appHeader__link"
      href="https://github.com/coombeben/portfolio"
      target="_blank"
      rel="noreferrer"
    >
      <span className="appHeader__linkIcon" aria-hidden="true">
        <svg viewBox="0 0 24 24" role="img">
          <path
            fill="currentColor"
            d="M12 2C6.477 2 2 6.655 2 12.402c0 4.59 2.865 8.484 6.839 9.86.5.095.682-.22.682-.495 0-.244-.01-1.05-.014-1.905-2.782.625-3.369-1.232-3.369-1.232-.455-1.204-1.11-1.525-1.11-1.525-.908-.648.068-.635.068-.635 1.003.074 1.532 1.07 1.532 1.07.892 1.59 2.341 1.131 2.913.864.09-.67.35-1.132.636-1.393-2.221-.264-4.556-1.154-4.556-5.138 0-1.136.39-2.064 1.03-2.792-.103-.262-.446-1.322.097-2.756 0 0 .84-.279 2.75 1.067A9.1 9.1 0 0 1 12 6.846c.826.004 1.66.115 2.438.335 1.909-1.346 2.748-1.067 2.748-1.067.545 1.434.202 2.494.1 2.756.64.728 1.028 1.656 1.028 2.792 0 3.994-2.34 4.87-4.57 5.129.359.324.679.961.679 1.939 0 1.4-.013 2.53-.013 2.875 0 .277.18.596.688.494C19.137 20.88 22 16.992 22 12.402 22 6.655 17.523 2 12 2Z"
          />
        </svg>
      </span>
      View Source
    </a>
  </header>
}