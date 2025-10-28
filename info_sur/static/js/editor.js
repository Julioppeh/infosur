const tabs = document.querySelectorAll('.tab-button');
const tabPanels = document.querySelectorAll('.tab-content');
const createForm = document.getElementById('create-form');
const createOutput = document.getElementById('create-output');
const satireSlider = document.getElementById('satire-level');
const satireValue = document.getElementById('satire-value');
const articlesList = document.getElementById('articles-list');
const articleTemplate = document.getElementById('article-item-template');
const editPanel = document.getElementById('edit-panel');
const editForm = document.getElementById('edit-form');
const editOutput = document.getElementById('edit-output');
const templateEditor = document.getElementById('template-editor');
const templateOutput = document.getElementById('template-output');
const saveTemplateBtn = document.getElementById('save-template');

let articlesCache = [];

function switchTab(targetTab) {
    tabs.forEach((tab) => {
        const isActive = tab.dataset.tab === targetTab;
        tab.classList.toggle('active', isActive);
        tab.setAttribute('aria-selected', String(isActive));
    });
    tabPanels.forEach((panel) => {
        const isActive = panel.id === `tab-${targetTab}`;
        panel.classList.toggle('active', isActive);
        panel.setAttribute('aria-hidden', String(!isActive));
    });
}

tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
        switchTab(tab.dataset.tab);
        if (tab.dataset.tab === 'manage') {
            loadArticles();
        }
        if (tab.dataset.tab === 'template') {
            loadTemplate();
        }
    });
});

satireSlider?.addEventListener('input', () => {
    satireValue.textContent = satireSlider.value;
});

async function createArticle(event) {
    event.preventDefault();
    createOutput.textContent = 'Generando artículo…';

    const formData = new FormData(createForm);
    const payload = {
        prompt: formData.get('prompt'),
        satire_level: Number(formData.get('satire_level')),
        image_prompts: [
            formData.get('image_prompt_primary'),
            formData.get('image_prompt_secondary'),
        ].filter(Boolean),
    };

    try {
        const response = await fetch('/api/articles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            let message = 'Error al generar el artículo';
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                const errorData = await response.json();
                message = errorData.error || message;
            } else {
                const errorText = await response.text();
                message = errorText || message;
            }
            throw new Error(message.trim());
        }

        const data = await response.json();
        createOutput.textContent = `Artículo creado correctamente. Slug: ${data.slug}`;
        createForm.reset();
        satireValue.textContent = '50';
        articlesCache = [];
        loadArticles();
    } catch (error) {
        console.error(error);
        createOutput.textContent = `Error: ${error.message}`;
    }
}

createForm?.addEventListener('submit', createArticle);

async function loadArticles() {
    try {
        const response = await fetch('/api/articles');
        if (!response.ok) throw new Error('No se pudo cargar la lista de artículos');
        articlesCache = await response.json();
        renderArticles();
    } catch (error) {
        console.error(error);
        articlesList.textContent = 'Error cargando artículos';
    }
}

function renderArticles() {
    articlesList.innerHTML = '';
    if (!articlesCache.length) {
        articlesList.textContent = 'No hay artículos guardados todavía.';
        return;
    }

    articlesCache.forEach((article) => {
        const node = articleTemplate.content.cloneNode(true);
        node.querySelector('h3').textContent = article.title || 'Sin título';
        node.querySelector('.meta').textContent = `${article.slug} · ${new Date(article.created_at).toLocaleString('es-ES')}`;
        node.querySelector('.view').href = `/${article.slug}`;
        node.querySelector('.edit').addEventListener('click', () => openEditor(article.id));
        node.querySelector('.delete').addEventListener('click', () => deleteArticle(article.id));
        articlesList.appendChild(node);
    });
}

async function openEditor(articleId) {
    try {
        const response = await fetch(`/api/articles/${articleId}`);
        if (!response.ok) throw new Error('No se pudo cargar el artículo');
        const data = await response.json();
        populateEditor(data);
    } catch (error) {
        console.error(error);
        editOutput.textContent = `Error cargando artículo: ${error.message}`;
    }
}

function populateEditor(article) {
    editPanel.hidden = false;
    editForm.article_id.value = article.id;
    const articleData = article.article_data || {};
    const temas = articleData.temas || [];

    [...editForm.elements].forEach((el) => {
        if (!el.name || el.name === 'article_id') return;
        if (articleData[el.name]) {
            el.value = articleData[el.name];
        } else if (el.name === 'temas') {
            el.value = temas.join(', ');
        } else if (el.name === 'image_primary') {
            el.value = article.image_data?.primary || '';
        } else if (el.name === 'image_secondary') {
            el.value = article.image_data?.secondary || '';
        } else {
            el.value = '';
        }
    });
}

async function submitEdit(event) {
    event.preventDefault();
    const formData = new FormData(editForm);
    const articleId = formData.get('article_id');

    const articleData = {};
    for (const [key, value] of formData.entries()) {
        if (!value || key === 'article_id' || key === 'temas' || key.startsWith('image_')) continue;
        articleData[key] = value;
    }

    const payload = {
        article_data: articleData,
        temas: formData.get('temas')
            ? formData.get('temas').split(',').map((t) => t.trim()).filter(Boolean)
            : [],
        image_data: {
            primary: formData.get('image_primary') || null,
            secondary: formData.get('image_secondary') || null,
        },
    };

    try {
        const response = await fetch(`/api/articles/${articleId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!response.ok) throw new Error('No se pudo guardar el artículo');
        editOutput.textContent = 'Cambios guardados correctamente';
        articlesCache = [];
        loadArticles();
    } catch (error) {
        console.error(error);
        editOutput.textContent = `Error guardando: ${error.message}`;
    }
}

editForm?.addEventListener('submit', submitEdit);

async function deleteArticle(articleId) {
    if (!confirm('¿Seguro que quieres eliminar este artículo?')) return;
    try {
        const response = await fetch(`/api/articles/${articleId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Error al eliminar');
        loadArticles();
    } catch (error) {
        console.error(error);
        alert(`No se pudo eliminar: ${error.message}`);
    }
}

async function loadTemplate() {
    if (templateEditor.dataset.loaded) return;
    try {
        const response = await fetch('/api/template');
        if (!response.ok) throw new Error('No se pudo cargar el template');
        const data = await response.json();
        templateEditor.value = data.template;
        templateEditor.dataset.loaded = 'true';
    } catch (error) {
        console.error(error);
        templateOutput.textContent = `Error: ${error.message}`;
    }
}

async function saveTemplate() {
    try {
        const response = await fetch('/api/template', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ template: templateEditor.value }),
        });
        if (!response.ok) throw new Error('No se pudo guardar el template');
        templateOutput.textContent = 'Template guardado correctamente';
    } catch (error) {
        console.error(error);
        templateOutput.textContent = `Error guardando template: ${error.message}`;
    }
}

saveTemplateBtn?.addEventListener('click', saveTemplate);

// Inicialización
switchTab('create');
