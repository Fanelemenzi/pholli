/**
 * Mobile Optimizations for Pholli Insurance Platform
 * Enhances mobile user experience with touch-friendly interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Mobile detection
    const isMobile = window.innerWidth <= 768;
    const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    // Add mobile class to body
    if (isMobile) {
        document.body.classList.add('mobile-device');
    }
    
    if (isTouch) {
        document.body.classList.add('touch-device');
    }
    
    // Mobile navigation enhancements
    initMobileNavigation();
    
    // Form optimizations
    initMobileFormOptimizations();
    
    // Touch-friendly interactions
    initTouchOptimizations();
    
    // Performance optimizations
    initPerformanceOptimizations();
    
    // Viewport height fix for mobile browsers
    initViewportFix();
});

/**
 * Mobile Navigation Enhancements
 */
function initMobileNavigation() {
    const navToggle = document.querySelector('.mobile-nav-toggle');
    const navMenu = document.querySelector('.navmenu');
    
    if (navToggle && navMenu) {
        // Improve mobile menu accessibility
        navToggle.setAttribute('aria-label', 'Toggle navigation menu');
        navToggle.setAttribute('aria-expanded', 'false');
        
        navToggle.addEventListener('click', function() {
            const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
            navToggle.setAttribute('aria-expanded', !isExpanded);
            
            // Add smooth animation
            if (!isExpanded) {
                navMenu.style.display = 'block';
                setTimeout(() => navMenu.classList.add('show'), 10);
            } else {
                navMenu.classList.remove('show');
                setTimeout(() => navMenu.style.display = 'none', 300);
            }
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!navMenu.contains(e.target) && !navToggle.contains(e.target)) {
                navMenu.classList.remove('show');
                navToggle.setAttribute('aria-expanded', 'false');
            }
        });
        
        // Close menu when clicking on a link
        const navLinks = navMenu.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('show');
                navToggle.setAttribute('aria-expanded', 'false');
            });
        });
    }
}

/**
 * Mobile Form Optimizations
 */
function initMobileFormOptimizations() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Prevent zoom on input focus for iOS
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.type !== 'range' && input.type !== 'checkbox' && input.type !== 'radio') {
                // Ensure font-size is at least 16px to prevent zoom
                const computedStyle = window.getComputedStyle(input);
                const fontSize = parseFloat(computedStyle.fontSize);
                if (fontSize < 16) {
                    input.style.fontSize = '16px';
                }
            }
        });
        
        // Add loading states for form submissions
        const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
        submitButtons.forEach(button => {
            form.addEventListener('submit', function() {
                button.disabled = true;
                const originalText = button.textContent || button.value;
                button.textContent = 'Processing...';
                button.classList.add('loading');
                
                // Re-enable after 10 seconds as fallback
                setTimeout(() => {
                    button.disabled = false;
                    button.textContent = originalText;
                    button.classList.remove('loading');
                }, 10000);
            });
        });
    });
    
    // Improve select dropdowns on mobile
    const selects = document.querySelectorAll('select');
    selects.forEach(select => {
        select.addEventListener('focus', function() {
            this.size = Math.min(this.options.length, 5);
        });
        
        select.addEventListener('blur', function() {
            this.size = 1;
        });
        
        select.addEventListener('change', function() {
            this.size = 1;
        });
    });
}

/**
 * Touch-friendly Interactions
 */
function initTouchOptimizations() {
    // Add touch feedback to buttons
    const buttons = document.querySelectorAll('.btn, button, .nav-link, .card');
    buttons.forEach(button => {
        button.addEventListener('touchstart', function() {
            this.classList.add('touch-active');
        });
        
        button.addEventListener('touchend', function() {
            setTimeout(() => this.classList.remove('touch-active'), 150);
        });
        
        button.addEventListener('touchcancel', function() {
            this.classList.remove('touch-active');
        });
    });
    
    // Improve tab navigation for touch
    const tabLinks = document.querySelectorAll('.nav-tabs .nav-link');
    tabLinks.forEach(tab => {
        tab.addEventListener('touchstart', function(e) {
            e.preventDefault();
            this.click();
        });
    });
    
    // Add swipe gestures for carousels/sliders
    const sliders = document.querySelectorAll('.swiper, .carousel');
    sliders.forEach(slider => {
        let startX = 0;
        let startY = 0;
        let distX = 0;
        let distY = 0;
        
        slider.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });
        
        slider.addEventListener('touchmove', function(e) {
            if (!startX || !startY) return;
            
            distX = e.touches[0].clientX - startX;
            distY = e.touches[0].clientY - startY;
            
            // Prevent vertical scrolling during horizontal swipe
            if (Math.abs(distX) > Math.abs(distY)) {
                e.preventDefault();
            }
        });
        
        slider.addEventListener('touchend', function() {
            if (Math.abs(distX) > 50) {
                // Trigger swipe event
                const swipeEvent = new CustomEvent('swipe', {
                    detail: { direction: distX > 0 ? 'right' : 'left' }
                });
                this.dispatchEvent(swipeEvent);
            }
            
            startX = 0;
            startY = 0;
            distX = 0;
            distY = 0;
        });
    });
}

/**
 * Performance Optimizations
 */
function initPerformanceOptimizations() {
    // Lazy load images
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
    
    // Optimize animations for mobile
    const animatedElements = document.querySelectorAll('[data-aos]');
    if (window.innerWidth <= 768) {
        animatedElements.forEach(el => {
            el.setAttribute('data-aos-duration', '300');
            el.setAttribute('data-aos-delay', '0');
        });
    }
    
    // Reduce motion for users who prefer it
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.documentElement.style.setProperty('--animation-duration', '0.01ms');
        animatedElements.forEach(el => {
            el.removeAttribute('data-aos');
        });