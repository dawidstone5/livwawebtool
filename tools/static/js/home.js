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






// LIVWA Enhanced Home Page JavaScript
// Handles carousel navigation, smooth scrolling, and animations

document.addEventListener('DOMContentLoaded', function() {
    
    // ===================================
    // Smooth Scroll for Anchor Links
    // ===================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    const offsetTop = target.offsetTop - 80; // Account for fixed navbar
                    window.scrollTo({
                        top: offsetTop,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // ===================================
    // Carousel Navigation (if using arrows)
    // ===================================
    const prevButton = document.querySelector('.carousel-prev');
    const nextButton = document.querySelector('.carousel-next');
    const carousel = document.querySelector('.tools-carousel');
    
    if (prevButton && nextButton && carousel) {
        // For grid layout, we can implement horizontal scroll
        // but since we're using CSS Grid, let's add smooth scroll behavior
        
        prevButton.addEventListener('click', function() {
            const cards = document.querySelectorAll('.tool-card');
            if (cards.length > 0) {
                const cardWidth = cards[0].offsetWidth;
                const gap = parseFloat(getComputedStyle(carousel).gap) || 40;
                carousel.scrollBy({
                    left: -(cardWidth + gap),
                    behavior: 'smooth'
                });
            }
        });
        
        nextButton.addEventListener('click', function() {
            const cards = document.querySelectorAll('.tool-card');
            if (cards.length > 0) {
                const cardWidth = cards[0].offsetWidth;
                const gap = parseFloat(getComputedStyle(carousel).gap) || 40;
                carousel.scrollBy({
                    left: cardWidth + gap,
                    behavior: 'smooth'
                });
            }
        });
        
        // Hide/show navigation buttons based on scroll position
        function updateCarouselNav() {
            const isAtStart = carousel.scrollLeft <= 10;
            const isAtEnd = carousel.scrollLeft >= carousel.scrollWidth - carousel.clientWidth - 10;
            
            prevButton.style.opacity = isAtStart ? '0.3' : '0.85';
            prevButton.style.pointerEvents = isAtStart ? 'none' : 'auto';
            
            nextButton.style.opacity = isAtEnd ? '0.3' : '0.85';
            nextButton.style.pointerEvents = isAtEnd ? 'none' : 'auto';
        }
        
        // Make carousel scrollable
        carousel.style.overflowX = 'auto';
        carousel.style.scrollBehavior = 'smooth';
        carousel.style.scrollSnapType = 'x mandatory';
        
        // Add scroll snap to cards
        document.querySelectorAll('.tool-card').forEach(card => {
            card.style.scrollSnapAlign = 'start';
        });
        
        carousel.addEventListener('scroll', updateCarouselNav);
        updateCarouselNav();
    }

    // ===================================
    // Animate on Scroll (Simple AOS)
    // ===================================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('aos-animate');
                // Optionally unobserve after animation
                // observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe all elements with data-aos attribute
    document.querySelectorAll('[data-aos]').forEach(el => {
        observer.observe(el);
    });

    // ===================================
    // Scroll Indicator Animation
    // ===================================
    const scrollIndicator = document.querySelector('.scroll-indicator');
    if (scrollIndicator) {
        scrollIndicator.addEventListener('click', function() {
            const aboutSection = document.querySelector('.section-about');
            if (aboutSection) {
                window.scrollTo({
                    top: aboutSection.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });

        // Hide scroll indicator after scrolling
        let lastScrollTop = 0;
        window.addEventListener('scroll', function() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            if (scrollTop > 100 && scrollIndicator) {
                scrollIndicator.style.opacity = '0';
                scrollIndicator.style.pointerEvents = 'none';
            } else if (scrollTop <= 100 && scrollIndicator) {
                scrollIndicator.style.opacity = '1';
                scrollIndicator.style.pointerEvents = 'auto';
            }
            lastScrollTop = scrollTop;
        });
    }

    // ===================================
    // Parallax Effect for Hero Section
    // ===================================
    const heroSection = document.querySelector('.hero-section');
    const heroImage = document.querySelector('.hero-image');
    
    if (heroSection && heroImage) {
        window.addEventListener('scroll', function() {
            const scrolled = window.pageYOffset;
            const heroHeight = heroSection.offsetHeight;
            
            if (scrolled <= heroHeight) {
                const parallaxSpeed = 0.5;
                heroImage.style.transform = `translateY(${scrolled * parallaxSpeed}px)`;
            }
        });
    }

    // ===================================
    // Add hover sound effect (optional)
    // ===================================
    const cards = document.querySelectorAll('.tool-card, .team-card, .partner-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        });
    });

    // ===================================
    // Loading Animation
    // ===================================
    window.addEventListener('load', function() {
        document.body.classList.add('loaded');
        
        // Trigger initial animations
        const initialElements = document.querySelectorAll('[data-aos]');
        initialElements.forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.top < window.innerHeight) {
                el.classList.add('aos-animate');
            }
        });
    });

    // ===================================
    // Mobile Menu Enhancement
    // ===================================
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            document.body.classList.toggle('menu-open');
        });
    }

    // ===================================
    // Stats Counter Animation
    // ===================================
    function animateCounter(element, target, duration = 2000) {
        const start = 0;
        const increment = target / (duration / 16); // 60fps
        let current = start;
        
        const timer = setInterval(function() {
            current += increment;
            if (current >= target) {
                element.textContent = target.toLocaleString();
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current).toLocaleString();
            }
        }, 16);
    }

    // Observe stats section and animate when visible
    const statsSection = document.querySelector('.section-stats');
    if (statsSection) {
        const statsObserver = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const statNumbers = entry.target.querySelectorAll('.stat-number');
                    statNumbers.forEach(stat => {
                        const text = stat.textContent.trim();
                        // Extract number (handle formats like "30M+", "95%", "1M+")
                        const match = text.match(/[\d,]+/);
                        if (match) {
                            const number = parseInt(match[0].replace(/,/g, ''));
                            animateCounter(stat, number);
                        }
                    });
                    statsObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.3 });
        
        statsObserver.observe(statsSection);
    }

    // ===================================
    // Keyboard Navigation for Carousel
    // ===================================
    if (carousel) {
        document.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowLeft' && prevButton) {
                prevButton.click();
            } else if (e.key === 'ArrowRight' && nextButton) {
                nextButton.click();
            }
        });
    }

    // ===================================
    // Performance Optimization: Debounce
    // ===================================
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Apply debounce to scroll events
    const debouncedScrollHandler = debounce(function() {
        // Any scroll-heavy operations can go here
    }, 100);

    window.addEventListener('scroll', debouncedScrollHandler);

    // ===================================
    // Print Console Welcome Message
    // ===================================
    console.log('%c🌊 LIVWA - Lake Victoria Advanced Water Management', 
        'font-size: 16px; font-weight: bold; color: #3498db;');
    console.log('%cEmpowering Action Through Accurate Water Data', 
        'font-size: 12px; color: #1abc9c;');
});

