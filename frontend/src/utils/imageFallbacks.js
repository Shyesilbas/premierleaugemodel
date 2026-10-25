// Hide a broken image instead of swapping in another club's badge.
export function handleImageFallback(event, fallbackSrc = null) {
  const image = event.currentTarget;
  if (!fallbackSrc || image.dataset.fallbackApplied) {
    image.style.display = 'none';
    return;
  }
  image.dataset.fallbackApplied = 'true';
  image.src = fallbackSrc;
}

export function handleTeamBadgeError(event) {
  handleImageFallback(event);
}
