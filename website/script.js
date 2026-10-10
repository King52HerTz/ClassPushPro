document.addEventListener('DOMContentLoaded', () => {
    initSnowCanvas();
    initSmoothScroll();
    initNavbarEffect();
    initViewToggle();
    initMobileMenu();
    const badge = document.querySelector('.badge-new');
    if (badge) fetch('version.json', { cache: 'no-store' }).then(response => response.json()).then(release => {
        badge.textContent = `v${release.version} · ${release.release_status || '正式发布'}`;
    }).catch(() => { badge.textContent = 'ClassPush · 云端与日历'; });
});

/* --- 移动端菜单逻辑 --- */
function initMobileMenu() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            const icon = mobileMenuBtn.querySelector('i');
            if (navLinks.classList.contains('active')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    }
}

/* --- 视图切换逻辑 --- */
function initViewToggle() {
    const toggles = document.querySelectorAll('.view-toggle-btn');
    const views = document.querySelectorAll('.view-content');

    if (toggles.length === 0) return;

    toggles.forEach(btn => {
        btn.addEventListener('click', () => {
            // 移除所有激活状态
            toggles.forEach(t => t.classList.remove('active'));
            views.forEach(v => v.classList.remove('active'));

            // 激活当前按钮
            btn.classList.add('active');
            
            // 显示对应视图
            const targetId = btn.getAttribute('data-target');
            const targetView = document.getElementById(targetId);
            if (targetView) {
                targetView.classList.add('active');
            }
        });
    });
}

/* --- 雪花/粒子效果 --- */
function initSnowCanvas() {
    const canvas = document.getElementById('snowCanvas');
    const ctx = canvas.getContext('2d');
    
    let width, height;
    let particles = [];
    
    // 窗口大小处理
    const resize = () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    };
    
    window.addEventListener('resize', resize);
    resize();

    // 粒子类
    class Particle {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = Math.random() * 0.5 + 0.2;
            this.size = Math.random() * 3 + 1;
            this.alpha = Math.random() * 0.5 + 0.1;
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            // Wrap around screen
            if (this.y > height) this.y = -10;
            if (this.x > width) this.x = 0;
            // 屏幕边界环绕
            if (this.x < 0) this.x = width;
        }

        draw() {
            ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha})`;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    // 初始化粒子
    for (let i = 0; i < 100; i++) {
        particles.push(new Particle());
    }

    // 动画循环
    function animate() {
        ctx.clearRect(0, 0, width, height);
        
        particles.forEach(p => {
            p.update();
            p.draw();
        });

        requestAnimationFrame(animate);
    }

    animate();
}

/* --- 锚点链接平滑滚动 --- */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                // 关闭移动端菜单（可选实现）
                // document.querySelector('.mobile-menu-btn')?.click();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/* --- 导航栏滚动玻璃效果 --- */
function initNavbarEffect() {
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(255, 255, 255, 0.95)';
            navbar.style.boxShadow = '0 5px 20px rgba(0,0,0,0.05)';
        } else {
            navbar.style.background = 'rgba(255, 255, 255, 0.8)';
            navbar.style.boxShadow = 'none';
        }
    });
}
