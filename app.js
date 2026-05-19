const DATA_URL = 'iba_cocktails_translated.json';
const IMAGE_DATA_URL = 'cocktail_images.json';

let currentLang = 'ko';
let currentFilter = 'all';
let cocktails = [];
let categoryOrder = [];
let cocktailImages = {};

const elements = {};

document.addEventListener('DOMContentLoaded', () => {
    elements.mainContainer = document.getElementById('mainContainer');
    elements.spiritFilter = document.getElementById('spiritFilter');
    elements.btnKo = document.getElementById('btnKo');
    elements.btnEn = document.getElementById('btnEn');
    elements.modalOverlay = document.getElementById('modalOverlay');
    elements.modalTitle = document.getElementById('modalTitle');
    elements.modalPhotoSection = document.getElementById('modalPhotoSection');
    elements.modalPhoto = document.getElementById('modalPhoto');
    elements.modalPhotoCredit = document.getElementById('modalPhotoCredit');
    elements.modalIngredients = document.getElementById('modalIngredients');
    elements.modalRecipeLabel = document.getElementById('modalRecipeLabel');
    elements.modalMethod = document.getElementById('modalMethod');
    elements.modalGarnishSection = document.getElementById('modalGarnishSection');
    elements.modalGarnishLabel = document.getElementById('modalGarnishLabel');
    elements.modalGarnish = document.getElementById('modalGarnish');

    elements.btnKo.addEventListener('click', () => setLanguage('ko'));
    elements.btnEn.addEventListener('click', () => setLanguage('en'));
    elements.spiritFilter.addEventListener('change', event => setFilter(event.target.value));
    document.getElementById('closeModalButton').addEventListener('click', closeModal);
    elements.modalOverlay.addEventListener('click', event => {
        if (event.target === elements.modalOverlay) closeModal();
    });

    Promise.all([
        fetch(DATA_URL).then(res => res.json()),
        fetch(IMAGE_DATA_URL)
            .then(res => res.json())
            .catch(err => {
                console.warn('이미지 메타데이터 로드 에러:', err);
                return { images: {} };
            })
    ])
        .then(([data, imageData]) => {
            cocktails = data;
            cocktailImages = imageData.images || {};
            categoryOrder = buildCategoryOrder(data);
            renderGallery();
        })
        .catch(err => console.error('데이터 로드 에러:', err));
});

function setLanguage(lang) {
    currentLang = lang;
    elements.btnKo.className = lang === 'ko' ? 'active' : '';
    elements.btnEn.className = lang === 'en' ? 'active' : '';
    renderGallery();
}

function setFilter(spirit) {
    currentFilter = spirit;
    renderGallery();
}

function buildCategoryOrder(data) {
    const seen = new Set();

    return [...data]
        .sort((a, b) => getName(a, 'ko').localeCompare(getName(b, 'ko'), 'ko'))
        .map(getCategory)
        .filter(category => {
            if (seen.has(category)) return false;
            seen.add(category);
            return true;
        });
}

function getCategory(cocktail) {
    return cocktail.category || 'Others';
}

function getName(cocktail, lang = currentLang) {
    if (lang === 'ko' && cocktail.name_ko && cocktail.name_ko.trim() !== '') {
        return cocktail.name_ko;
    }

    return cocktail.name;
}

function renderGallery() {
    elements.mainContainer.innerHTML = '';

    if (cocktails.length === 0) return;

    const groupedData = getFilteredCocktails()
        .sort((a, b) => getName(a).localeCompare(getName(b), currentLang === 'ko' ? 'ko' : 'en'))
        .reduce((acc, cocktail) => {
            const category = getCategory(cocktail);
            if (!acc[category]) acc[category] = [];
            acc[category].push(cocktail);
            return acc;
        }, {});

    if (Object.keys(groupedData).length === 0) {
        elements.mainContainer.innerHTML = '<div class="no-results">선택하신 주류가 들어간 칵테일이 없습니다. 🥺</div>';
        return;
    }

    const visibleCategories = getOrderedCategories(groupedData);
    visibleCategories.forEach(categoryName => {
        const section = document.createElement('div');
        section.className = 'category-section';

        const header = document.createElement('h2');
        header.className = 'category-header';
        header.innerText = categoryName;
        section.appendChild(header);

        const gallery = document.createElement('div');
        gallery.className = 'gallery';

        groupedData[categoryName].forEach(cocktail => {
            const card = document.createElement('div');
            card.className = 'card';

            const title = document.createElement('h3');
            title.innerText = getName(cocktail);
            card.appendChild(title);
            card.addEventListener('click', () => openModal(cocktail));
            gallery.appendChild(card);
        });

        section.appendChild(gallery);
        elements.mainContainer.appendChild(section);
    });
}

function getOrderedCategories(groupedData) {
    const existingCategories = Object.keys(groupedData);
    const knownCategories = categoryOrder.filter(category => existingCategories.includes(category));
    const newCategories = existingCategories
        .filter(category => !categoryOrder.includes(category))
        .sort((a, b) => a.localeCompare(b));

    return [...knownCategories, ...newCategories];
}

function getFilteredCocktails() {
    return cocktails.filter(cocktail => {
        if (currentFilter === 'all') return true;
        if (!cocktail.ingredients) return false;

        return cocktail.ingredients.some(ingredient => {
            const ingName = (ingredient.ingredient || ingredient.special || '').toLowerCase();

            if (currentFilter === 'whiskey') {
                return ingName.includes('whiskey') || ingName.includes('bourbon') || ingName.includes('rye');
            }

            if (currentFilter === 'cognac') {
                return ingName.includes('cognac') || ingName.includes('brandy');
            }

            return ingName.includes(currentFilter);
        });
    });
}

function openModal(cocktail) {
    const method = currentLang === 'ko' && cocktail.method_ko && cocktail.method_ko.trim() !== ''
        ? cocktail.method_ko
        : cocktail.method || cocktail.preparation;

    elements.modalTitle.innerText = getName(cocktail);
    elements.modalRecipeLabel.innerText = currentLang === 'ko' ? '레시피' : 'Recipe';
    elements.modalMethod.innerText = method || '제조법 정보가 없습니다.';

    renderPhoto(cocktail);
    renderGarnish(cocktail);
    renderIngredients(cocktail);

    elements.modalOverlay.classList.add('is-open');
}

function renderPhoto(cocktail) {
    const image = cocktailImages[cocktail.name];

    if (!image) {
        elements.modalPhotoSection.hidden = true;
        elements.modalPhoto.removeAttribute('src');
        elements.modalPhotoCredit.replaceChildren();
        return;
    }

    elements.modalPhoto.src = image.src;
    elements.modalPhoto.alt = `${getName(cocktail)} photo`;
    elements.modalPhotoSection.hidden = false;
    renderPhotoCredit(image);
}

function renderPhotoCredit(image) {
    elements.modalPhotoCredit.replaceChildren();

    const author = image.author || image.credit || 'Wikimedia Commons contributor';
    const sourceLink = document.createElement('a');
    sourceLink.href = image.sourcePage;
    sourceLink.target = '_blank';
    sourceLink.rel = 'noopener noreferrer';
    sourceLink.innerText = author;

    const licenseText = image.license || image.usageTerms || 'license';
    const licenseLink = document.createElement('a');
    licenseLink.href = image.licenseUrl || image.sourcePage;
    licenseLink.target = '_blank';
    licenseLink.rel = 'noopener noreferrer';
    licenseLink.innerText = licenseText;

    const prefix = currentLang === 'ko' ? '사진: ' : 'Photo: ';
    const separator = currentLang === 'ko' ? ' / 라이선스: ' : ' / License: ';

    elements.modalPhotoCredit.append(prefix, sourceLink, separator, licenseLink);
}

function renderGarnish(cocktail) {
    const garnish = currentLang === 'ko' && cocktail.garnish_ko && cocktail.garnish_ko.trim() !== ''
        ? cocktail.garnish_ko
        : cocktail.garnish || '';

    if (garnish.trim() !== '') {
        elements.modalGarnishLabel.innerText = currentLang === 'ko' ? '가니시' : 'Garnish';
        elements.modalGarnish.innerText = garnish;
        elements.modalGarnishSection.style.display = 'block';
    } else {
        elements.modalGarnishSection.style.display = 'none';
    }
}

function renderIngredients(cocktail) {
    elements.modalIngredients.innerHTML = '';

    if (!cocktail.ingredients) return;

    cocktail.ingredients.forEach(ingredient => {
        const li = document.createElement('li');
        const qtyText = (ingredient.quantity || ingredient.amount || '').toString();
        const unitText = ingredient.unit || '';
        const fullQty = `${qtyText} ${unitText}`.trim();

        if (fullQty) {
            const badge = document.createElement('span');
            badge.className = 'qty-badge';
            badge.innerText = fullQty;
            li.appendChild(badge);
        }

        const name = document.createElement('span');
        name.innerText = currentLang === 'ko' && ingredient.ingredient_ko && ingredient.ingredient_ko.trim() !== ''
            ? ingredient.ingredient_ko
            : ingredient.ingredient || ingredient.special || '';
        li.appendChild(name);

        elements.modalIngredients.appendChild(li);
    });
}

function closeModal() {
    elements.modalOverlay.classList.remove('is-open');
}
