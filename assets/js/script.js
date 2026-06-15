function initializeApp() {
    setupThemeToggle();
    setupAppShell();
    setupResponsiveMenu();
    setupNotifications();
    setupSidebarCalendar();
    setupFeedInteractions();
    setupFileUploads();
}

function setupAppShell() {
    const sidebar = document.querySelector("[data-app-sidebar]");
    const toggle = document.querySelector("[data-sidebar-toggle]");
    const overlay = document.querySelector("[data-sidebar-overlay]");

    if (!sidebar || !toggle || !overlay) {
        return;
    }

    const closeSidebar = () => {
        sidebar.classList.remove("is-open");
        overlay.classList.remove("is-visible");
        document.body.classList.remove("menu-open");
        toggle.setAttribute("aria-expanded", "false");
    };

    toggle.addEventListener("click", () => {
        const isOpen = sidebar.classList.toggle("is-open");
        overlay.classList.toggle("is-visible", isOpen);
        document.body.classList.toggle("menu-open", isOpen);
        toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    overlay.addEventListener("click", closeSidebar);

    sidebar.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 1080) {
                closeSidebar();
            }
        });
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > 1080) {
            closeSidebar();
        }
    });
}

function setupNotifications() {
    const toggle = document.querySelector("[data-notif-toggle]");
    const dropdown = document.querySelector("[data-notif-dropdown]");

    if (!toggle || !dropdown) return;

    toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.classList.toggle("is-open");
    });

    document.addEventListener("click", (e) => {
        if (!dropdown.contains(e.target) && !toggle.contains(e.target)) {
            dropdown.classList.remove("is-open");
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeApp);
} else {
    initializeApp();
}

function setupThemeToggle() {
    const themeBtn = document.createElement("button");
    themeBtn.className = "theme-toggle-btn";
    themeBtn.textContent = "\u{1F319}";
    themeBtn.title = "Alternar tema";
    themeBtn.setAttribute("aria-label", "Alternar tema escuro");
    document.body.appendChild(themeBtn);

    if (localStorage.getItem("theme") === "dark") {
        document.body.classList.add("dark-mode");
        themeBtn.textContent = "\u2600\uFE0F";
        themeBtn.setAttribute("aria-label", "Alternar tema claro");
    }

    themeBtn.addEventListener("click", () => {
        document.body.classList.toggle("dark-mode");
        const isDark = document.body.classList.contains("dark-mode");
        themeBtn.textContent = isDark ? "\u2600\uFE0F" : "\u{1F319}";
        themeBtn.setAttribute("aria-label", isDark ? "Alternar tema claro" : "Alternar tema escuro");
        localStorage.setItem("theme", isDark ? "dark" : "light");
    });
}

function setupResponsiveMenu() {
    const menuToggle = document.querySelector(".menu-toggle");
    const navbar = document.querySelector(".main-header .navbar:not(.navbar-static)");
    const navOverlay = document.querySelector(".nav-overlay");
    const navLinks = navbar ? navbar.querySelectorAll("a[href]") : [];

    function closeMenu() {
        if (!menuToggle || !navbar) {
            return;
        }
        menuToggle.classList.remove("is-active");
        menuToggle.setAttribute("aria-expanded", "false");
        navbar.classList.remove("is-open");
        document.body.classList.remove("menu-open");
    }

    function openMenu() {
        if (!menuToggle || !navbar) {
            return;
        }
        menuToggle.classList.add("is-active");
        menuToggle.setAttribute("aria-expanded", "true");
        navbar.classList.add("is-open");
        document.body.classList.add("menu-open");
    }

    if (menuToggle && navbar) {
        menuToggle.addEventListener("click", () => {
            const isOpen = navbar.classList.contains("is-open");
            if (isOpen) {
                closeMenu();
            } else {
                openMenu();
            }
        });

        navLinks.forEach((link) => {
            link.addEventListener("click", () => {
                if (window.innerWidth <= 768) {
                    closeMenu();
                }
            });
        });

        if (navOverlay) {
            navOverlay.addEventListener("click", closeMenu);
        }

        window.addEventListener("resize", () => {
            if (window.innerWidth > 768) {
                closeMenu();
            }
        });
    }
}

function setupSidebarCalendar() {
    const calendarViews = document.querySelectorAll("[data-calendar]");
    if (!calendarViews.length) {
        return;
    }

    const eventsNode = document.getElementById("calendar-events-data");
    const backendEvents = safeJsonParse(eventsNode ? eventsNode.textContent : "[]");
    const calendarState = {
        viewDate: new Date(),
        selectedDate: null,
    };

    document.querySelectorAll("[data-calendar-prev]").forEach((button) => {
        button.addEventListener("click", () => {
            calendarState.viewDate.setMonth(calendarState.viewDate.getMonth() - 1);
            calendarState.selectedDate = null;
            renderCalendars();
        });
    });

    document.querySelectorAll("[data-calendar-next]").forEach((button) => {
        button.addEventListener("click", () => {
            calendarState.viewDate.setMonth(calendarState.viewDate.getMonth() + 1);
            calendarState.selectedDate = null;
            renderCalendars();
        });
    });

    function renderCalendars() {
        const year = calendarState.viewDate.getFullYear();
        const month = calendarState.viewDate.getMonth();
        const title = formatMonthTitle(calendarState.viewDate);
        const todayKey = formatDateKey(new Date());
        const firstDay = new Date(year, month, 1);
        const startOffset = (firstDay.getDay() + 6) % 7;
        const startDate = new Date(year, month, 1 - startOffset);
        const totalCells = 42;
        const weekdayLabels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"];

        document.querySelectorAll("[data-calendar-title]").forEach((titleElement) => {
            titleElement.textContent = title;
        });

        calendarViews.forEach((calendar) => {
            const cells = weekdayLabels.map((weekday) => `<span class="weekday">${weekday}</span>`).join("");
            let days = "";

            for (let index = 0; index < totalCells; index += 1) {
                const cellDate = new Date(startDate);
                cellDate.setDate(startDate.getDate() + index);
                const cellKey = formatDateKey(cellDate);
                const events = getEventsForDate(cellKey);
                const classes = [];

                if (cellDate.getMonth() !== month) {
                    classes.push("muted-day");
                }
                if (cellKey === todayKey) {
                    classes.push("today");
                }
                if (events.length) {
                    classes.push("event-day");
                }
                if (cellKey === calendarState.selectedDate) {
                    classes.push("selected-day");
                }

                const classAttr = classes.length ? ` class="${classes.join(" ")}"` : "";
                const tooltip = events.map((event) => escapeHtml(event.title)).join(" | ");
                days += `<button type="button"${classAttr} data-date="${cellKey}" title="${tooltip}">${cellDate.getDate()}</button>`;
            }

            calendar.innerHTML = cells + days;
            calendar.querySelectorAll("[data-date]").forEach((dayButton) => {
                dayButton.addEventListener("click", () => {
                    calendarState.selectedDate = dayButton.dataset.date;
                    renderCalendars();
                });
            });
        });

        renderCalendarEvents(year, month);
    }

    function renderCalendarEvents(year, month) {
        const selectedDate = calendarState.selectedDate ? parseDateKey(calendarState.selectedDate) : null;
        const selectedInView = selectedDate && selectedDate.getFullYear() === year && selectedDate.getMonth() === month;
        const events = selectedInView
            ? getEventsForDate(calendarState.selectedDate)
            : backendEvents.filter((event) => {
                const eventDate = parseDateKey(event.date);
                return eventDate.getFullYear() === year && eventDate.getMonth() === month;
            });

        document.querySelectorAll("[data-calendar-events]").forEach((eventList) => {
            if (!events.length) {
                eventList.innerHTML = `
                    <div class="empty-events">
                        <strong>${selectedInView ? formatDayTitle(selectedDate) : formatMonthTitle(calendarState.viewDate)}</strong>
                        <span class="muted-text">Sem eventos cadastrados.</span>
                    </div>
                `;
                return;
            }

            eventList.innerHTML = events.map((event) => {
                const eventClass = sanitizeClassName(event.event_type || event.type);
                return `
                    <div class="calendar-event-item">
                        <span class="event-pill ${eventClass}">${escapeHtml(event.type)}</span>
                        <strong>${formatDayTitle(parseDateKey(event.date))}</strong>
                        <span class="muted-text">
                            ${escapeHtml(event.title)} • ${escapeHtml(event.classroom || "Geral")}
                            ${event.subject ? ` • ${escapeHtml(event.subject)}` : ""}
                        </span>
                    </div>
                `;
            }).join("");
        });
    }

    function sanitizeClassName(value) {
        return String(value)
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/(^-|-$)/g, "");
    }

    function getEventsForDate(dateKey) {
        return backendEvents.filter((event) => event.date === dateKey);
    }

    renderCalendars();
}

function setupFeedInteractions() {
    const csrfToken = getCsrfToken();
    const postForm = document.querySelector(".ajax-post-form");
    const feedList = document.querySelector("[data-feed-list]");
    const aiReviewButton = document.querySelector("[data-ai-review-btn]");

    if (postForm && aiReviewButton) {
        aiReviewButton.addEventListener("click", async () => {
            const titleInput = postForm.querySelector("#id_post-title");
            const contentInput = postForm.querySelector("#id_post-content");
            const messageNode = postForm.querySelector("[data-post-form-message]");

            if (!contentInput || !contentInput.value.trim()) {
                if (messageNode) {
                    messageNode.textContent = "Escreva a publicação antes de pedir revisão.";
                }
                return;
            }

            aiReviewButton.disabled = true;
            aiReviewButton.classList.add("loading");
            if (messageNode) {
                messageNode.innerHTML = '<span class="spinner"></span> Analisando conteúdo...';
                messageNode.style.color = "var(--brand-primary)";
            }

            try {
                const response = await fetch(postForm.dataset.aiReviewUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: new URLSearchParams({
                        title: titleInput ? titleInput.value : "",
                        content: contentInput.value,
                    }),
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.error || "IA temporariamente indisponível. Tente novamente.");
                }
                if (titleInput && payload.reviewed.title) {
                    titleInput.value = payload.reviewed.title;
                }
                contentInput.value = payload.reviewed.content || contentInput.value;
                if (messageNode) {
                    const source = payload.meta && payload.meta.used_api ? "OpenRouter" : "fallback local";
                    messageNode.textContent = `✨ Revisão concluída via ${source}.`;
                    messageNode.style.color = "#10b981";
                }
            } catch (error) {
                if (messageNode) {
                    messageNode.textContent = "⚠️ " + (error.message || "Erro de conexão.");
                    messageNode.style.color = "#ef4444";
                }
            } finally {
                aiReviewButton.disabled = false;
                aiReviewButton.classList.remove("loading");
            }
        });
    }

    if (postForm) {
        postForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const feedListContainer = document.querySelector("[data-feed-list]");
            const submitButton = postForm.querySelector("button[type='submit']") || 
                                 document.querySelector(`button[type="submit"][form="${postForm.id}"]`);
            const messageNode = postForm.querySelector("[data-post-form-message]");
            const formData = new FormData(postForm);

            if (!submitButton) return;
            
            submitButton.disabled = true;
            submitButton.classList.add("loading");
            if (messageNode) messageNode.textContent = "Publicando...";

            try {
                const url = postForm.dataset.createPostUrl || window.location.pathname;
                const response = await fetch(url, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: formData,
                });

                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(flattenFormErrors(payload.errors) || "Nao foi possivel publicar.");
                }

                if (feedListContainer) {
                    const emptyState = feedListContainer.querySelector("[data-feed-empty-state]");
                    if (emptyState) {
                        const emptyCard = emptyState.closest(".card");
                        if (emptyCard) emptyCard.remove();
                        else emptyState.remove();
                    }
                    feedListContainer.insertAdjacentHTML("afterbegin", renderPostCard(payload.post));
                    hydratePostCard(feedListContainer.firstElementChild, getCsrfToken());
                }
                
                postForm.reset();
                if (messageNode) {
                    messageNode.textContent = "Publicacao enviada e colocada no topo.";
                    messageNode.style.color = "#10b981";
                }
            } catch (error) {
                if (messageNode) {
                    messageNode.textContent = error.message || "Erro ao publicar.";
                    messageNode.style.color = "#ef4444";
                }
                console.error(error);
            } finally {
                submitButton.disabled = false;
                submitButton.classList.remove("loading");
            }
        });
    }

    // Reaction buttons: optimistic UI + graceful rollback on error
    document.querySelectorAll("[data-post-id]").forEach((postCard) => {
        hydratePostCard(postCard, csrfToken);
    });

    document.querySelectorAll("[data-comment-id]").forEach((commentCard) => {
        hydrateCommentDeletion(commentCard, csrfToken);
    });
}

function setupFileUploads() {
    document.querySelectorAll("[data-file-upload]").forEach((wrapper) => {
        const input = wrapper.querySelector("input[type='file']");
        const label = wrapper.querySelector("[data-file-upload-text]");

        if (!input || !label) {
            return;
        }

        const renderFileState = () => {
            if (input.files && input.files.length) {
                const file = input.files[0];
                const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
                label.textContent = `${file.name} · ${sizeMb} MB`;
                wrapper.classList.add("has-file");
            } else {
                label.textContent = "Nenhum arquivo selecionado";
                wrapper.classList.remove("has-file");
            }
        };

        input.addEventListener("change", renderFileState);
        renderFileState();
    });
}

function hydratePostCard(postCard, csrfToken) {
    if (!postCard || postCard.dataset.bound === "true") {
        return;
    }
    postCard.dataset.bound = "true";

    const reactButton = postCard.querySelector("[data-react-url]");
    if (reactButton) {
        reactButton.setAttribute("aria-pressed", reactButton.classList.contains("is-active") ? "true" : "false");
        reactButton.addEventListener("click", async () => {
            const button = reactButton;
            const postCard = button.closest("[data-post-id]");
            const countEl = postCard ? postCard.querySelector("[data-like-count]") : null;
            const currentActive = button.classList.contains("is-active");
            // optimistic update
            const optimisticActive = !currentActive;
            button.classList.toggle("is-active", optimisticActive);
            button.setAttribute("aria-pressed", optimisticActive ? "true" : "false");
            if (countEl) {
                const n = parseInt((countEl.textContent || "0").replace(/[^0-9-]/g, ""), 10) || 0;
                countEl.textContent = `${optimisticActive ? n + 1 : Math.max(0, n - 1)} curtida(s)`;
            }
            button.classList.add("loading");
            try {
                const response = await fetch(button.dataset.reactUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: new URLSearchParams({
                        post_id: button.dataset.postId,
                        reaction_type: button.dataset.reactionType,
                    }),
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.error || "Falha ao curtir.");
                }
                // apply authoritative state from server
                renderReactionState(postCard, payload);
            } catch (error) {
                // rollback optimistic UI
                button.classList.toggle("is-active", currentActive);
                button.setAttribute("aria-pressed", currentActive ? "true" : "false");
                if (countEl) {
                    const n = parseInt((countEl.textContent || "0").replace(/[^0-9-]/g, ""), 10) || 0;
                    countEl.textContent = `${currentActive ? n + 1 : Math.max(0, n - 1)} curtida(s)`;
                }
                console.error(error);
                window.alert(error.message || "Erro ao processar curtida.");
            } finally {
                button.classList.remove("loading");
            }
        });
    }

    const commentFocusButton = postCard.querySelector("[data-comment-focus]");
    if (commentFocusButton) {
        const button = commentFocusButton;
        button.addEventListener("click", () => {
            const postCard = button.closest("[data-post-id]");
            const textarea = postCard ? postCard.querySelector("textarea[name='comment-content']") : null;
            if (!textarea) {
                return;
            }
            textarea.focus();
            textarea.scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
    }

    const commentForm = postCard.querySelector(".ajax-comment-form");
    if (commentForm) {
        const form = commentForm;
        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const textarea = form.querySelector("textarea[name='comment-content']");
            const postCard = form.closest("[data-post-id]");
            const stream = postCard ? postCard.querySelector("[data-comment-stream]") : null;
            const commentCount = postCard ? postCard.querySelector("[data-comment-count]") : null;
            const submitBtn = form.querySelector("button[type='submit']");
            const originalBtnText = submitBtn ? submitBtn.innerHTML : null;
            const postIdInput = form.querySelector("input[name='post_id']");

            if (!textarea || !submitBtn || !postIdInput || !stream || !commentCount) {
                return;
            }

            const content = textarea.value.trim();
            if (!content) {
                textarea.focus();
                return;
            }

            submitBtn.disabled = true;
            submitBtn.classList.add("loading");
            submitBtn.innerHTML = `<span class="spinner" aria-hidden="true"></span> Enviando...`;

            try {
                const response = await fetch(form.dataset.commentUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: new URLSearchParams({
                        post_id: postIdInput.value,
                        "comment-content": content,
                    }),
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.error || "Nao foi possivel enviar o comentario.");
                }
                const emptyState = stream.querySelector("[data-empty-comments]");
                if (emptyState) {
                    emptyState.remove();
                }
                stream.insertAdjacentHTML("beforeend", renderComment(payload.comment));
                hydrateCommentDeletion(stream.lastElementChild, csrfToken);
                commentCount.textContent = `${payload.comment_count} comentario(s)`;
                textarea.value = "";
                textarea.focus();
            } catch (error) {
                window.alert(error.message);
                console.error(error);
            } finally {
                submitBtn.disabled = false;
                submitBtn.classList.remove("loading");
                if (originalBtnText) {
                    submitBtn.innerHTML = originalBtnText;
                }
            }
        });
    }
}

function renderReactionState(postCard, payload) {
    const button = postCard.querySelector("[data-react-url]");
    const count = postCard.querySelector("[data-like-count]");
    if (button) {
        button.classList.toggle("is-active", payload.current_user_reaction === "like");
    }
    if (count) {
        count.textContent = `${payload.total} curtida(s)`;
    }
}

function renderComment(comment) {
    const avatar = comment.avatar
        ? `<img src="${escapeHtml(comment.avatar)}" alt="${escapeHtml(comment.author)}">`
        : `<span>${escapeHtml(comment.initials)}</span>`;
    const deleteButton = comment.can_delete
        ? `
            <button
                type="button"
                class="comment-delete-btn"
                data-comment-delete-url="/feed/comments/delete/"
                data-comment-id="${comment.id}"
            >
                Excluir
            </button>
        `
        : "";
    return `
        <div class="comment-card" data-comment-id="${comment.id}">
            <div class="comment-avatar">${avatar}</div>
            <div class="comment-body">
                <strong>${escapeHtml(comment.author)}</strong>
                <span class="muted-text">${escapeHtml(comment.created_at)}</span>
                <p>${escapeHtml(comment.content)}</p>
                ${deleteButton}
            </div>
        </div>
    `;
}

function renderPostCard(post) {
    const attachmentMarkup = !post.attachment_url
        ? ""
        : `
            ${post.attachment_is_image ? `<p><img src="${escapeHtml(post.attachment_url)}" alt="${escapeHtml(post.title)}" class="post-cover-image"></p>` : ""}
            <p class="attachment-chip">
                <span>${escapeHtml(post.attachment_extension)}</span>
                <a href="${escapeHtml(post.attachment_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(post.attachment_name)}</a>
            </p>
        `;
    const deleteMarkup = post.can_delete
        ? `
            <form method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="${escapeHtml(getCsrfToken())}">
                <input type="hidden" name="action" value="delete_post">
                <input type="hidden" name="post_id" value="${post.id}">
                <button class="action-btn" type="submit">Excluir</button>
            </form>
        `
        : "";

    return `
        <article class="card live-post-card" id="post-${post.id}" data-post-id="${post.id}">
            <div class="post-header">
                <div class="avatar avatar-brand">${escapeHtml(post.author_initials)}</div>
                <div class="user-info">
                    <h4>
                        ${escapeHtml(post.title)}
                        ${post.is_pinned ? '<span class="pill-highlight">Fixado</span>' : ""}
                    </h4>
                    <span>
                        ${escapeHtml(post.author)} - ${escapeHtml(post.classroom)}
                        ${post.subject ? ` - ${escapeHtml(post.subject)}` : ""}
                        - ${escapeHtml(post.created_at)}
                    </span>
                </div>
            </div>
            <div class="post-content">
                <p>${escapeHtml(post.content).replace(/\n/g, "<br>")}</p>
                ${attachmentMarkup}
            </div>
            <div class="post-actions">
                <button
                    type="button"
                    class="action-btn action-btn-heart"
                    data-react-url="${escapeHtml(post.react_url)}"
                    data-post-id="${post.id}"
                    data-reaction-type="like"
                    aria-label="Curtir publicacao"
                >
                    <span aria-hidden="true">&#10084;</span>
                    <span>Curtir</span>
                </button>
                <span class="action-stat" data-like-count>${post.reaction_payload.total} curtida(s)</span>
                <button type="button" class="action-btn" data-comment-focus>
                    <span aria-hidden="true">&#128172;</span>
                    <span data-comment-count>${post.comment_count} comentario(s)</span>
                </button>
                ${deleteMarkup}
            </div>
            <div class="card post-comments-card">
                <h4 class="widget-title">Comentarios</h4>
                <div class="comment-stream" data-comment-stream>
                    <p class="muted-text" data-empty-comments>Nenhum comentario ainda.</p>
                </div>
                <form method="post" class="contact-form ajax-comment-form" data-comment-url="${escapeHtml(post.comment_url)}">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${escapeHtml(getCsrfToken())}">
                    <input type="hidden" name="post_id" value="${post.id}">
                    <div class="form-group">
                        <label class="label-left" for="comment-${post.id}">Adicionar comentario</label>
                        <textarea id="comment-${post.id}" name="comment-content" rows="2" placeholder="Escreva seu comentario."></textarea>
                    </div>
                    <button type="submit" class="btn btn-secondary btn-compact">
                        <span aria-hidden="true">&#128172;</span> Comentar
                    </button>
                </form>
            </div>
        </article>
    `;
}

function hydrateCommentDeletion(commentCard, csrfToken) {
    const deleteButton = commentCard.querySelector("[data-comment-delete-url]");
    if (!deleteButton || deleteButton.dataset.bound === "true") {
        return;
    }
    deleteButton.dataset.bound = "true";
    deleteButton.addEventListener("click", async () => {
        const postCard = commentCard.closest("[data-post-id]");
        const commentCount = postCard.querySelector("[data-comment-count]");
        const stream = postCard.querySelector("[data-comment-stream]");

        try {
            const response = await fetch(deleteButton.dataset.commentDeleteUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: new URLSearchParams({
                    comment_id: deleteButton.dataset.commentId,
                }),
            });
            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.error || "Nao foi possivel excluir o comentario.");
            }
            commentCard.remove();
            commentCount.textContent = `${payload.comment_count} comentario(s)`;
            if (stream && !stream.querySelector("[data-comment-id]")) {
                stream.innerHTML = '<p class="muted-text" data-empty-comments>Nenhum comentario ainda.</p>';
            }
        } catch (error) {
            window.alert(error.message);
        }
    });
}

function getCsrfToken() {
    if (window.CSRF_TOKEN) return window.CSRF_TOKEN;
    
    const tokenInput = document.querySelector("input[name='csrfmiddlewaretoken']");
    if (tokenInput && tokenInput.value) return tokenInput.value;

    const match = document.cookie.match(/(^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[2]) : "";
}

function safeJsonParse(value) {
    try {
        return JSON.parse(value || "[]");
    } catch (error) {
        return [];
    }
}

function formatDateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function parseDateKey(dateKey) {
    const [year, month, day] = dateKey.split("-").map(Number);
    return new Date(year, month - 1, day);
}

function formatMonthTitle(date) {
    const title = new Intl.DateTimeFormat("pt-BR", {
        month: "long",
        year: "numeric",
    }).format(date);
    return title.charAt(0).toUpperCase() + title.slice(1);
}

function formatDayTitle(date) {
    return new Intl.DateTimeFormat("pt-BR", {
        day: "2-digit",
        month: "short",
    }).format(date).replace(".", "");
}

function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#039;",
    }[char]));
}

function flattenFormErrors(errors) {
    if (!errors) {
        return "";
    }
    return Object.values(errors)
        .flat()
        .map((item) => item.message || item)
        .join(" ");
}
