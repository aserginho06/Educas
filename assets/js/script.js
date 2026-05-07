document.addEventListener('DOMContentLoaded', () => {
    const themeBtn = document.createElement('button');
    themeBtn.className = 'theme-toggle-btn';
    themeBtn.textContent = '\u{1F319}';
    themeBtn.title = 'Alternar tema';
    themeBtn.setAttribute('aria-label', 'Alternar tema escuro');
    document.body.appendChild(themeBtn);

    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
        themeBtn.textContent = '\u2600\uFE0F';
        themeBtn.setAttribute('aria-label', 'Alternar tema claro');
    }

    themeBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        themeBtn.textContent = isDark ? '\u2600\uFE0F' : '\u{1F319}';
        themeBtn.setAttribute('aria-label', isDark ? 'Alternar tema claro' : 'Alternar tema escuro');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });

    const menuToggle = document.querySelector('.menu-toggle');
    const navbar = document.querySelector('.main-header .navbar:not(.navbar-static)');
    const navOverlay = document.querySelector('.nav-overlay');
    const navLinks = navbar ? navbar.querySelectorAll('a[href]') : [];

    function closeMenu() {
        if (!menuToggle || !navbar) {
            return;
        }

        menuToggle.classList.remove('is-active');
        menuToggle.setAttribute('aria-expanded', 'false');
        navbar.classList.remove('is-open');
        document.body.classList.remove('menu-open');
    }

    function openMenu() {
        if (!menuToggle || !navbar) {
            return;
        }

        menuToggle.classList.add('is-active');
        menuToggle.setAttribute('aria-expanded', 'true');
        navbar.classList.add('is-open');
        document.body.classList.add('menu-open');
    }

    if (menuToggle && navbar) {
        menuToggle.addEventListener('click', () => {
            const isOpen = navbar.classList.contains('is-open');
            if (isOpen) {
                closeMenu();
            } else {
                openMenu();
            }
        });

        navLinks.forEach((link) => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    closeMenu();
                }
            });
        });

        if (navOverlay) {
            navOverlay.addEventListener('click', closeMenu);
        }

        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                closeMenu();
            }
        });
    }

    const calendarViews = document.querySelectorAll('[data-calendar]');
    const calendarState = {
        viewDate: new Date(),
        selectedDate: null
    };
    const defaultAcademicEvents = [
        {
            date: '2026-05-08',
            title: 'Simulado de Matematica',
            shortTitle: 'Simulado'
        },
        {
            date: '2026-05-15',
            title: 'Entrega de Historia',
            shortTitle: 'Historia'
        },
        {
            date: '2026-05-20',
            title: 'Lista de Funcoes',
            shortTitle: 'Lista'
        },
        {
            date: '2026-05-29',
            title: 'Relatorio de Biologia',
            shortTitle: 'Biologia'
        }
    ];
    let customAcademicEvents = loadCustomAcademicEvents();

    if (calendarViews.length) {
        document.querySelectorAll('[data-calendar-prev]').forEach((button) => {
            button.addEventListener('click', () => {
                calendarState.viewDate.setMonth(calendarState.viewDate.getMonth() - 1);
                calendarState.selectedDate = null;
                renderCalendars();
            });
        });

        document.querySelectorAll('[data-calendar-next]').forEach((button) => {
            button.addEventListener('click', () => {
                calendarState.viewDate.setMonth(calendarState.viewDate.getMonth() + 1);
                calendarState.selectedDate = null;
                renderCalendars();
            });
        });

        document.querySelectorAll('[data-calendar-add]').forEach((button) => {
            button.addEventListener('click', addCustomAcademicEvent);
        });

        renderCalendars();
    }

    function renderCalendars() {
        const year = calendarState.viewDate.getFullYear();
        const month = calendarState.viewDate.getMonth();
        const title = formatMonthTitle(calendarState.viewDate);
        const todayKey = formatDateKey(new Date());
        const firstDay = new Date(year, month, 1);
        const startOffset = (firstDay.getDay() + 6) % 7;
        const startDate = new Date(year, month, 1 - startOffset);
        const totalCells = 42;
        const weekdayLabels = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'];

        document.querySelectorAll('[data-calendar-title]').forEach((titleElement) => {
            titleElement.textContent = title;
        });

        calendarViews.forEach((calendar) => {
            const isLarge = calendar.dataset.calendar === 'large';
            const cells = weekdayLabels
                .map((weekday) => `<span class="weekday">${weekday}</span>`)
                .join('');
            let days = '';

            for (let index = 0; index < totalCells; index += 1) {
                const cellDate = new Date(startDate);
                cellDate.setDate(startDate.getDate() + index);
                const cellKey = formatDateKey(cellDate);
                const events = getEventsForDate(cellKey);
                const classes = [];

                if (cellDate.getMonth() !== month) {
                    classes.push('muted-day');
                }

                if (cellKey === todayKey) {
                    classes.push('today');
                }

                if (events.length) {
                    classes.push('event-day');
                }

                if (cellKey === calendarState.selectedDate) {
                    classes.push('selected-day');
                }

                const classAttr = classes.length ? ` class="${classes.join(' ')}"` : '';

                if (isLarge) {
                    const eventLabel = events[0] ? `<span>${escapeHtml(events[0].shortTitle)}</span>` : '';
                    const eventText = events[0] ? `, ${events[0].title}` : '';
                    days += `<button type="button"${classAttr} data-date="${cellKey}" aria-label="${cellDate.getDate()} de ${title}${eventText}">${cellDate.getDate()}${eventLabel}</button>`;
                } else {
                    days += `<span${classAttr}>${cellDate.getDate()}</span>`;
                }
            }

            calendar.innerHTML = cells + days;
            calendar.setAttribute('aria-label', `Calendario de ${title}`);

            if (isLarge) {
                calendar.querySelectorAll('[data-date]').forEach((dayButton) => {
                    dayButton.addEventListener('click', () => {
                        calendarState.selectedDate = dayButton.dataset.date;
                        renderCalendars();
                    });
                });
            }
        });

        renderCalendarEvents(year, month);
    }

    function renderCalendarEvents(year, month) {
        const selectedDate = calendarState.selectedDate ? parseDateKey(calendarState.selectedDate) : null;
        const selectedInView = selectedDate
            && selectedDate.getFullYear() === year
            && selectedDate.getMonth() === month;
        const events = selectedInView
            ? getEventsForDate(calendarState.selectedDate)
            : getAllCalendarEvents().filter((event) => {
                const eventDate = parseDateKey(event.date);
                return eventDate.getFullYear() === year && eventDate.getMonth() === month;
            });

        document.querySelectorAll('[data-calendar-events]').forEach((eventList) => {
            if (!events.length) {
                const emptyLabel = selectedInView
                    ? formatDayTitle(selectedDate)
                    : formatMonthTitle(calendarState.viewDate);
                eventList.innerHTML = `
                    <div class="empty-events">
                        <strong>${emptyLabel}</strong>
                        <span class="muted-text">Sem eventos cadastrados.</span>
                    </div>
                `;
                return;
            }

            eventList.innerHTML = events
                .map((event) => {
                    const eventDate = parseDateKey(event.date);
                    return `
                        <div>
                            <strong>${formatDayTitle(eventDate)}</strong>
                            <span class="muted-text">${escapeHtml(event.title)}</span>
                        </div>
                    `;
                })
                .join('');
        });
    }

    function getEventsForDate(dateKey) {
        return getAllCalendarEvents().filter((event) => event.date === dateKey);
    }

    function getAllCalendarEvents() {
        return [...defaultAcademicEvents, ...customAcademicEvents];
    }

    function addCustomAcademicEvent() {
        const fallbackDate = calendarState.selectedDate || formatDateKey(calendarState.viewDate);
        const rawDate = window.prompt('Data do evento (AAAA-MM-DD ou DD/MM/AAAA)', fallbackDate);

        if (!rawDate) {
            return;
        }

        const eventDate = normalizeEventDate(rawDate);

        if (!eventDate) {
            window.alert('Use uma data valida, como 2026-05-20 ou 20/05/2026.');
            return;
        }

        const title = window.prompt('Titulo do evento');

        if (!title || !title.trim()) {
            return;
        }

        const cleanedTitle = title.trim();
        const event = {
            date: eventDate,
            title: cleanedTitle,
            shortTitle: cleanedTitle.split(/\s+/).slice(0, 2).join(' ')
        };
        const parsedDate = parseDateKey(eventDate);

        customAcademicEvents = [...customAcademicEvents, event];
        localStorage.setItem('educasCustomEvents', JSON.stringify(customAcademicEvents));
        calendarState.viewDate = new Date(parsedDate.getFullYear(), parsedDate.getMonth(), 1);
        calendarState.selectedDate = eventDate;
        renderCalendars();
    }

    function loadCustomAcademicEvents() {
        try {
            const savedEvents = JSON.parse(localStorage.getItem('educasCustomEvents') || '[]');
            return Array.isArray(savedEvents)
                ? savedEvents.filter((event) => event && event.date && event.title)
                : [];
        } catch (error) {
            return [];
        }
    }

    function normalizeEventDate(value) {
        const cleanValue = value.trim();
        let dateKey = '';
        const isoMatch = cleanValue.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        const brMatch = cleanValue.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);

        if (isoMatch) {
            dateKey = cleanValue;
        } else if (brMatch) {
            dateKey = `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
        } else {
            return null;
        }

        const parsedDate = parseDateKey(dateKey);
        return formatDateKey(parsedDate) === dateKey ? dateKey : null;
    }

    function formatDateKey(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function parseDateKey(dateKey) {
        const [year, month, day] = dateKey.split('-').map(Number);
        return new Date(year, month - 1, day);
    }

    function formatMonthTitle(date) {
        const title = new Intl.DateTimeFormat('pt-BR', {
            month: 'long',
            year: 'numeric'
        }).format(date);

        return title.charAt(0).toUpperCase() + title.slice(1);
    }

    function formatDayTitle(date) {
        return new Intl.DateTimeFormat('pt-BR', {
            day: '2-digit',
            month: 'short'
        }).format(date).replace('.', '');
    }

    function escapeHtml(value) {
        return value.replace(/[&<>"']/g, (char) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[char]));
    }

    const feedContainer = document.getElementById('feed-infinite-scroll');

    if (feedContainer) {
        window.addEventListener('scroll', () => {
            const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
            if (scrollTop + clientHeight >= scrollHeight - 100) {
                loadMorePosts();
            }
        });
    }

    let isLoading = false;

    function loadMorePosts() {
        if (!feedContainer || isLoading) {
            return;
        }

        isLoading = true;

        setTimeout(() => {
            const newPosts = generateRandomPosts(2);
            feedContainer.insertAdjacentHTML('beforeend', newPosts);
            isLoading = false;
        }, 500);
    }

    function generateRandomPosts(count) {
        const names = ['Prof. Amanda Silva', 'Secretaria Academica', 'Grupo de Estudos', 'Prof. Carlos Bio'];
        const contents = [
            'Nao esquecam que a data limite para entrega do trabalho e amanha!',
            'Novo evento cultural na escola na proxima semana. Inscrevam-se.',
            'Alguem tem as anotacoes da aula de Quimica?',
            'Lembrete: reuniao de pais e mestres nesta sexta-feira.'
        ];

        let html = '';

        for (let i = 0; i < count; i += 1) {
            const randomName = names[Math.floor(Math.random() * names.length)];
            const randomContent = contents[Math.floor(Math.random() * contents.length)];

            html += `
            <article class="card fade-in-up">
                <div class="post-header">
                    <div class="avatar avatar-default" role="img" aria-label="Avatar padrao do usuario"></div>
                    <div class="user-info">
                        <h4>${randomName}</h4>
                        <span>Recentemente</span>
                    </div>
                </div>
                <div class="post-content">
                    <p>${randomContent}</p>
                </div>
                <div class="post-actions">
                    <button class="action-btn emoji-action" aria-label="Curtir" title="Curtir">❤️</button>
                    <button class="action-btn emoji-action" aria-label="Comentar" title="Comentar">💬</button>
                    <button class="action-btn emoji-action" aria-label="Salvar" title="Salvar">🔖</button>
                </div>
            </article>
            `;
        }

        return html;
    }
});
