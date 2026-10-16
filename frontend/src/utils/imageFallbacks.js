export function handleImageFallback(event, fallbackSrc = '/badges/1.svg') {
  const image = event.currentTarget;
  if (image.dataset.fallbackApplied) {
    image.style.display = 'none';
    return;
  }
  image.dataset.fallbackApplied = 'true';
  image.src = fallbackSrc;
}

export function handleTeamBadgeError(event) {
  handleImageFallback(event);
}
