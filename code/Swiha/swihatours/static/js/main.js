/* =============================================
   SWIHA TOURS & TRAVEL — Global JavaScript
   ============================================= */

document.addEventListener("DOMContentLoaded", () => {
  // ── Navbar scroll effect ──────────────────────
  const navbar = document.querySelector(".navbar");
  const scrollThreshold = 60;

  function handleScroll() {
    if (window.scrollY > scrollThreshold) {
      navbar?.classList.add("scrolled");
    } else {
      navbar?.classList.remove("scrolled");
    }
    // Back to top button
    const btn = document.querySelector(".back-to-top");
    if (btn) {
      btn.classList.toggle("show", window.scrollY > 400);
    }
  }
  window.addEventListener("scroll", handleScroll, { passive: true });
  handleScroll();

  // ── Set active nav link ────────────────────────
  const currentPage = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-links a").forEach((link) => {
    if (link.getAttribute("href") === currentPage) {
      link.classList.add("active");
    }
  });

  // ── Mobile menu ───────────────────────────────
  const hamburger = document.querySelector(".hamburger");
  const mobileNav = document.querySelector(".mobile-nav");
  const closeBtn = document.querySelector(".mobile-nav .close-btn");

  hamburger?.addEventListener("click", () => {
    mobileNav?.classList.add("open");
    document.body.style.overflow = "hidden";
  });
  closeBtn?.addEventListener("click", closeMobileNav);
  mobileNav
    ?.querySelectorAll("a")
    .forEach((a) => a.addEventListener("click", closeMobileNav));

  function closeMobileNav() {
    mobileNav?.classList.remove("open");
    document.body.style.overflow = "";
  }

  // ── Back to top ───────────────────────────────
  document.querySelector(".back-to-top")?.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // ── Accordion ────────────────────────────────
  document.querySelectorAll(".accordion-header").forEach((header) => {
    header.addEventListener("click", () => {
      const item = header.closest(".accordion-item");
      const isOpen = item.classList.contains("open");
      document
        .querySelectorAll(".accordion-item")
        .forEach((i) => i.classList.remove("open"));
      if (!isOpen) item.classList.add("open");
    });
  });

  // ── Tabs ─────────────────────────────────────
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      const container = btn.closest(".tabs-container") || document;
      container
        .querySelectorAll(".tab-btn")
        .forEach((b) => b.classList.remove("active"));
      container
        .querySelectorAll(".tab-panel")
        .forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      container.querySelector(`#${target}`)?.classList.add("active");
    });
  });

  // ── Newsletter form (frontend placeholder) ────
  document.querySelectorAll(".newsletter-form").forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const input = form.querySelector('input[type="email"]');
      const email = input?.value.trim();
      if (email && isValidEmail(email)) {
        showToast("Thank you! You've been subscribed.", "success");
        if (input) input.value = "";
      } else {
        showToast("Please enter a valid email address.", "error");
      }
    });
  });

  // ── Contact / Booking forms (frontend placeholder) ─
  document.querySelectorAll("form.ajax-form").forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      const originalText = btn?.textContent;
      if (btn) {
        btn.textContent = "Sending…";
        btn.disabled = true;
      }
      // Simulate async — backend will replace this
      setTimeout(() => {
        showToast(
          "Your message has been received. We'll be in touch shortly!",
          "success",
        );
        form.reset();
        if (btn) {
          btn.textContent = originalText;
          btn.disabled = false;
        }
      }, 1200);
    });
  });

  // ── Toast notification ───────────────────────
  function showToast(message, type = "success") {
    const existing = document.querySelector(".toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      bottom: 80px;
      left: 50%;
      transform: translateX(-50%) translateY(20px);
      background: ${type === "success" ? "#2D6A4F" : "#c0392b"};
      color: white;
      padding: 14px 28px;
      border-radius: 4px;
      font-family: 'Inter', sans-serif;
      font-size: 0.9rem;
      font-weight: 500;
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
      z-index: 9999;
      opacity: 0;
      transition: all 0.35s ease;
      pointer-events: none;
    `;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
      toast.style.opacity = "1";
      toast.style.transform = "translateX(-50%) translateY(0)";
    });

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(-50%) translateY(20px)";
      setTimeout(() => toast.remove(), 400);
    }, 3500);
  }

  // ── Email validation helper ───────────────────
  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  // ── Lazy-load images with IntersectionObserver ─
  const lazyImages = document.querySelectorAll("img[data-src]");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.removeAttribute("data-src");
            observer.unobserve(img);
          }
        });
      },
      { rootMargin: "100px" },
    );
    lazyImages.forEach((img) => observer.observe(img));
  } else {
    lazyImages.forEach((img) => {
      img.src = img.dataset.src;
    });
  }

  // ── Scroll-reveal animation ───────────────────
  const revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && revealEls.length) {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 },
    );
    revealEls.forEach((el) => revealObserver.observe(el));
  }

  // ── Gallery lightbox (simple) ─────────────────
  document.querySelectorAll(".gallery-item").forEach((item) => {
    item.addEventListener("click", () => {
      const src = item.querySelector("img")?.src;
      if (!src) return;
      const overlay = document.createElement("div");
      overlay.style.cssText = `
        position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:9999;
        display:flex;align-items:center;justify-content:center;cursor:pointer;
      `;
      const img = document.createElement("img");
      img.src = src;
      img.style.cssText =
        "max-width:90vw;max-height:88vh;border-radius:4px;box-shadow:0 20px 60px rgba(0,0,0,0.5);";
      overlay.appendChild(img);
      overlay.addEventListener("click", () => overlay.remove());
      document.body.appendChild(overlay);
    });
  });

  // ── Smooth reveal CSS helper ──────────────────
  const style = document.createElement("style");
  style.textContent = `
    .reveal { opacity: 0; transform: translateY(24px); transition: opacity 0.65s ease, transform 0.65s ease; }
    .reveal.revealed { opacity: 1; transform: translateY(0); }
    .reveal-delay-1 { transition-delay: 0.1s; }
    .reveal-delay-2 { transition-delay: 0.2s; }
    .reveal-delay-3 { transition-delay: 0.3s; }
  `;
  document.head.appendChild(style);

  // ── Counter animation ─────────────────────────
  function animateCount(el) {
    const target = parseInt(el.dataset.count || el.textContent, 10);
    const duration = 1800;
    const start = performance.now();
    const update = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      el.textContent =
        Math.round(ease * target).toLocaleString() + (el.dataset.suffix || "");
      if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
  }

  const counterEls = document.querySelectorAll("[data-count]");
  if (counterEls.length && "IntersectionObserver" in window) {
    const counterObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            animateCount(entry.target);
            counterObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.5 },
    );
    counterEls.forEach((el) => counterObserver.observe(el));
  }
});
