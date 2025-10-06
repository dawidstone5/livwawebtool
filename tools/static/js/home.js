// tools/static/js/home.js
// This script handles the functionality of the tool cards on the home page.
document.addEventListener('DOMContentLoaded', function() {
  const scrollContainer = document.querySelector('.tools-scroll');
  const leftArrow = document.querySelector('.tools-arrow.left-arrow');
  const rightArrow = document.querySelector('.tools-arrow.right-arrow');
  const scrollAmount = 340; // Card width + gap

  leftArrow.addEventListener('click', () => {
    scrollContainer.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
  });
  rightArrow.addEventListener('click', () => {
    scrollContainer.scrollBy({ left: scrollAmount, behavior: 'smooth' });
  });
});
