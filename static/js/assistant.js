(function () {
    const root = document.querySelector('[data-ai-assistant]');
    if (!root) return;

    const userId = root.dataset.aiUserId || 'guest';
    const isAuthenticated = root.dataset.aiAuthenticated === 'true';
    const storageScope = isAuthenticated ? `user.${userId}` : 'guest';
    const STORAGE_MESSAGES = `artmarket.aiAssistant.messages.${storageScope}`;
    const STORAGE_OPEN = `artmarket.aiAssistant.open.${storageScope}`;
    const LEGACY_STORAGE_MESSAGES = 'artmarket.aiAssistant.messages';
    const LEGACY_STORAGE_OPEN = 'artmarket.aiAssistant.open';
    const MAX_HISTORY = 12;
    const MAX_CONTEXT = 8;

    const panel = root.querySelector('[data-ai-panel]');
    const toggle = root.querySelector('[data-ai-toggle]');
    const close = root.querySelector('[data-ai-close]');
    const form = root.querySelector('[data-ai-form]');
    const dropzone = root.querySelector('[data-ai-dropzone]');
    const preview = root.querySelector('[data-ai-preview]');
    const messages = root.querySelector('[data-ai-messages]');
    const selectedFiles = [];
    let conversationHistory = loadMessages();

    localStorage.removeItem(LEGACY_STORAGE_MESSAGES);
    localStorage.removeItem(LEGACY_STORAGE_OPEN);

    function loadMessages() {
        try {
            const saved = JSON.parse(localStorage.getItem(STORAGE_MESSAGES) || '[]');
            return Array.isArray(saved) ? saved.slice(-MAX_HISTORY) : [];
        } catch (error) {
            return [];
        }
    }

    function saveMessages() {
        try {
            localStorage.setItem(STORAGE_MESSAGES, JSON.stringify(conversationHistory.slice(-MAX_HISTORY)));
        } catch (error) {
            const textOnly = conversationHistory.map(item => ({ ...item, images: [] }));
            localStorage.setItem(STORAGE_MESSAGES, JSON.stringify(textOnly.slice(-MAX_HISTORY)));
        }
    }

    function openPanel() {
        panel.classList.add('is-open');
        panel.setAttribute('aria-hidden', 'false');
        localStorage.setItem(STORAGE_OPEN, 'true');
    }

    function closePanel() {
        panel.classList.remove('is-open');
        panel.setAttribute('aria-hidden', 'true');
        localStorage.setItem(STORAGE_OPEN, 'false');
    }

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    function messageClass(role) {
        if (role === 'user') return 'ai-message-user';
        if (role === 'error') return 'ai-message-error';
        return 'ai-message-bot';
    }

    function appendText(container, text) {
        if (!text) return;
        const body = document.createElement('div');
        body.className = 'ai-message-text';
        body.textContent = text;
        container.appendChild(body);
    }

    function appendImages(container, images) {
        if (!images || !images.length) return;
        const grid = document.createElement('div');
        grid.className = 'ai-message-images';
        images.forEach((src, index) => {
            const img = document.createElement('img');
            img.src = src;
            img.alt = `已发送图片 ${index + 1}`;
            grid.appendChild(img);
        });
        container.appendChild(grid);
    }

    function appendThinking(container, thinking, open) {
        if (!thinking || !Object.keys(thinking).length) return;
        const details = document.createElement('details');
        details.className = 'ai-thinking';
        details.open = Boolean(open);

        const summary = document.createElement('summary');
        summary.textContent = '分析过程';
        details.appendChild(summary);

        Object.entries(thinking).forEach(([title, value]) => {
            if (!value) return;
            const section = document.createElement('div');
            section.className = 'ai-thinking-section';
            const heading = document.createElement('strong');
            heading.textContent = title;
            const content = document.createElement('p');
            content.textContent = value;
            section.appendChild(heading);
            section.appendChild(content);
            details.appendChild(section);
        });
        container.appendChild(details);
        return details;
    }

    function renderMessage(message) {
        const item = document.createElement('div');
        item.className = `ai-message ${messageClass(message.role)}`;
        appendImages(item, message.images);
        appendText(item, message.text);
        appendThinking(item, message.thinking, message.thinkingOpen);
        messages.appendChild(item);
        scrollToBottom();
        return item;
    }

    function createStreamingAssistantMessage() {
        const item = document.createElement('div');
        item.className = 'ai-message ai-message-bot';

        const details = document.createElement('details');
        details.className = 'ai-thinking ai-thinking-live';
        details.open = true;

        const summary = document.createElement('summary');
        summary.textContent = '分析过程';
        const thinkingSection = document.createElement('div');
        thinkingSection.className = 'ai-thinking-section';
        const thinkingTitle = document.createElement('strong');
        thinkingTitle.textContent = '实时分析';
        const thinkingBody = document.createElement('p');
        thinkingBody.textContent = '';

        thinkingSection.appendChild(thinkingTitle);
        thinkingSection.appendChild(thinkingBody);
        details.appendChild(summary);
        details.appendChild(thinkingSection);

        const answerBody = document.createElement('div');
        answerBody.className = 'ai-message-text';
        answerBody.hidden = true;

        item.appendChild(details);
        item.appendChild(answerBody);
        messages.appendChild(item);
        scrollToBottom();

        return {
            item,
            details,
            summary,
            thinkingBody,
            answerBody,
            thinkingText: '',
            answerText: ''
        };
    }

    function renderConversation() {
        const intro = messages.querySelector('.ai-message-bot');
        messages.innerHTML = '';
        if (!conversationHistory.length && intro) {
            messages.appendChild(intro);
        } else if (!conversationHistory.length) {
            renderMessage({
                role: 'assistant',
                text: '上传艺术品图片可获取结构化鉴赏意见；也可以直接追问风格、技法、登记文案等艺术品相关问题。'
            });
        } else {
            conversationHistory.forEach(renderMessage);
        }
    }

    function rememberMessage(message) {
        conversationHistory.push(message);
        if (conversationHistory.length > MAX_HISTORY) {
            conversationHistory = conversationHistory.slice(-MAX_HISTORY);
        }
        saveMessages();
    }

    function buildContext() {
        return conversationHistory
            .slice(-MAX_CONTEXT)
            .map(item => `${item.role === 'user' ? '用户' : '智能体'}：${item.text || ''}`)
            .join('\n\n');
    }

    function addFiles(files) {
        Array.from(files)
            .filter(file => file.type.startsWith('image/'))
            .forEach(file => {
                if (selectedFiles.length < 5) selectedFiles.push(file);
            });
        renderPreview();
    }

    function fileToDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(file);
        });
    }

    async function selectedFileImages() {
        return Promise.all(selectedFiles.map(fileToDataURL));
    }

    async function readEventStream(response, handlers) {
        if (!response.body) {
            throw new Error('当前浏览器不支持流式响应');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const events = buffer.split('\n\n');
            buffer = events.pop() || '';

            for (const raw of events) {
                const lines = raw.split('\n');
                const eventLine = lines.find(line => line.startsWith('event:'));
                const dataLines = lines.filter(line => line.startsWith('data:'));
                if (!eventLine || !dataLines.length) continue;

                const eventName = eventLine.slice(6).trim();
                const dataText = dataLines.map(line => line.slice(5).trimStart()).join('\n');
                const payload = dataText ? JSON.parse(dataText) : {};
                if (handlers[eventName]) {
                    handlers[eventName](payload);
                }
                if (eventName === 'error') {
                    throw new Error(payload.error || '智能体调用失败');
                }
            }
        }
    }

    function renderPreview() {
        preview.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'ai-preview-item';

            const img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            img.alt = file.name;

            const button = document.createElement('button');
            button.type = 'button';
            button.setAttribute('aria-label', '移除图片');
            button.textContent = '×';
            button.addEventListener('click', () => {
                selectedFiles.splice(index, 1);
                renderPreview();
            });

            item.appendChild(img);
            item.appendChild(button);
            preview.appendChild(item);
        });
    }

    toggle.addEventListener('click', openPanel);
    close.addEventListener('click', closePanel);

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, event => {
            event.preventDefault();
            dropzone.classList.add('is-over');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, event => {
            event.preventDefault();
            dropzone.classList.remove('is-over');
        });
    });

    dropzone.addEventListener('drop', event => {
        addFiles(event.dataTransfer.files);
    });

    dropzone.addEventListener('paste', event => {
        addFiles(event.clipboardData.files);
    });

    panel.addEventListener('paste', event => {
        addFiles(event.clipboardData.files);
    });

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const message = form.elements.message.value.trim();
        if (!selectedFiles.length && !message) {
            renderMessage({ role: 'error', text: '请输入问题，或拖拽/粘贴图片进行鉴赏。' });
            return;
        }

        const submit = form.querySelector('button[type="submit"]');
        const images = await selectedFileImages();
        const userText = message || '请鉴赏这些图片';
        const userMessage = { role: 'user', text: userText, images };
        renderMessage(userMessage);
        rememberMessage(userMessage);

        const data = new FormData();
        data.append('message', message);
        data.append('context', buildContext());
        selectedFiles.forEach(file => data.append('images', file));

        selectedFiles.splice(0, selectedFiles.length);
        form.reset();
        renderPreview();

        const streaming = createStreamingAssistantMessage();
        submit.disabled = true;

        try {
            const response = await fetch('/api/assistant/appraise', {
                method: 'POST',
                body: data
            });
            if (!response.ok) {
                const contentType = response.headers.get('content-type') || '';
                const payload = contentType.includes('application/json')
                    ? await response.json()
                    : { error: await response.text() };
                const rawError = payload.error || '智能体调用失败';
                throw new Error(rawError.startsWith('<!DOCTYPE')
                    ? `服务返回了 HTML 错误页，状态码 ${response.status}。请确认服务已重启、接口路径正确，并检查后端日志。`
                    : rawError);
            }

            await readEventStream(response, {
                thinking_delta(payload) {
                    streaming.thinkingText += payload.delta || '';
                    streaming.thinkingBody.textContent = streaming.thinkingText;
                    scrollToBottom();
                },
                thinking_done() {
                    if (streaming.thinkingText) {
                        streaming.details.open = false;
                        streaming.details.classList.remove('ai-thinking-live');
                        streaming.summary.textContent = '分析过程（已完成）';
                    } else {
                        streaming.details.remove();
                    }
                    streaming.answerBody.hidden = false;
                    scrollToBottom();
                },
                answer_delta(payload) {
                    if (streaming.details.isConnected && streaming.details.open) {
                        streaming.details.open = false;
                        streaming.details.classList.remove('ai-thinking-live');
                        streaming.summary.textContent = '分析过程（已完成）';
                    }
                    streaming.answerText += payload.delta || '';
                    streaming.answerBody.hidden = false;
                    streaming.answerBody.textContent = streaming.answerText;
                    scrollToBottom();
                },
                done() {}
            });

            const assistantMessage = {
                role: 'assistant',
                text: streaming.answerText,
                thinking: streaming.thinkingText ? { 分析过程: streaming.thinkingText } : null,
                thinkingOpen: false
            };
            rememberMessage(assistantMessage);
        } catch (error) {
            streaming.item.remove();
            renderMessage({ role: 'error', text: error.message || '智能体调用失败' });
        } finally {
            submit.disabled = false;
        }
    });

    renderConversation();
    if (localStorage.getItem(STORAGE_OPEN) === 'true') {
        openPanel();
    }
})();
