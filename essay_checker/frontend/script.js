const API = 'http://127.0.0.1:8000';

const essay = document.querySelector('#essay');
const counter = document.querySelector('#counter');
const btn = document.querySelector('#reviewBtn');
const status = document.querySelector('#status');
const schoolInput = document.querySelector('#school');
const results = document.querySelector('#schoolResults');

let selectedSchool = '';
let timer;


// =========================================================
// 자기소개서 글자 수
// =========================================================

essay.addEventListener('input', () => {
    counter.textContent =
        `${essay.value.length.toLocaleString()}자`;
});


// =========================================================
// 학교 검색
// =========================================================

schoolInput.addEventListener('input', () => {
    selectedSchool = '';

    clearTimeout(timer);

    const q = schoolInput.value.trim();

    if (!q) {
        results.classList.add('hidden');
        return;
    }

    timer = setTimeout(() => {
        searchSchools(q);
    }, 180);
});


async function searchSchools(q) {
    try {
        const r = await fetch(
            `${API}/api/schools?q=${encodeURIComponent(q)}`
        );

        const data = await r.json();

        if (!data.length) {
            results.innerHTML =
                '<div class="result-item">검색 결과가 없습니다.</div>';

            results.classList.remove('hidden');
            return;
        }

        results.innerHTML = data.map(s => `
            <div
                class="result-item"
                data-name="${escapeHtml(s.name)}"
            >
                <span class="result-name">
                    ${escapeHtml(s.name)}
                </span>

                <span class="result-type">
                    ${escapeHtml(s.type)}
                </span>
            </div>
        `).join('');

        results.classList.remove('hidden');

        // 학교 클릭
        results
            .querySelectorAll('.result-item[data-name]')
            .forEach(el => {

                el.addEventListener('click', () => {
                    selectSchool(el);
                });

            });

    } catch (e) {

        results.innerHTML =
            '<div class="result-item">서버에 연결할 수 없습니다.</div>';

        results.classList.remove('hidden');
    }
}


// =========================================================
// 학교 선택
// =========================================================

function selectSchool(element) {
    selectedSchool = element.dataset.name;

    schoolInput.value = selectedSchool;

    results.classList.add('hidden');
}


// =========================================================
// 학교 검색 결과 바깥을 클릭하면 닫기
// =========================================================

document.addEventListener('click', e => {

    if (!e.target.closest('.autocomplete')) {
        results.classList.add('hidden');
    }

});


// =========================================================
// 자소서 컨펌
// =========================================================

btn.addEventListener('click', async () => {

    if (!essay.value.trim()) {
        status.textContent =
            '자기소개서를 먼저 입력하세요.';
        return;
    }

    if (!selectedSchool && !schoolInput.value.trim()) {
        status.textContent =
            '지원 학교를 입력하세요.';
        return;
    }

    btn.disabled = true;

    status.textContent =
        '자소서를 분석하고 있습니다...';

    try {

        const r = await fetch(`${API}/api/review`, {
            method: 'POST',

            headers: {
                'Content-Type': 'application/json'
            },

            body: JSON.stringify({
                school:
                    selectedSchool ||
                    schoolInput.value.trim(),

                question:
                    document.querySelector('#question').value,

                essay:
                    essay.value
            })
        });

        const data = await r.json();

        if (!r.ok) {
            throw new Error(
                data.detail ||
                '요청에 실패했습니다.'
            );
        }

        render(data.result);

        status.textContent =
            '컨펌이 완료되었습니다.';

    } catch (e) {

        status.textContent =
            e.message ||
            '오류가 발생했습니다.';

    } finally {

        btn.disabled = false;

    }

});


// =========================================================
// 결과 출력
// =========================================================

function render(x) {

    const sec =
        document.querySelector('#resultSection');

    const body =
        document.querySelector('#resultBody');

    let html = `
        <div class="summary">
            ${escapeHtml(
        x.summary ||
        '분석 결과가 없습니다.'
    )}
        </div>
    `;


    // -----------------------------------------------------
    // 확인이 필요한 내용
    // -----------------------------------------------------

    if (x.restricted?.length) {

        html += `
            <div class="section-title">
                확인이 필요한 내용
            </div>
        `;

        x.restricted.forEach(i => {

            html += `
                <div class="restricted">

                    <span class="badge">
                        ${escapeHtml(i.category)}
                    </span>

                    <p>
                        <b>
                            ${escapeHtml(i.text)}
                        </b>
                    </p>

                    <p>
                        ${escapeHtml(i.explanation)}
                    </p>
            `;

            if (i.questions?.length) {

                html += i.questions
                    .map(q => `
                        <div class="question-item">
                            ${escapeHtml(q)}
                        </div>
                    `)
                    .join('');
            }

            html += `
                </div>
            `;
        });
    }


    // -----------------------------------------------------
    // 수정 방향
    // -----------------------------------------------------

    if (x.issues?.length) {

        html += `
            <div class="section-title">
                수정 방향
            </div>
        `;

        x.issues.forEach(i => {

            html += `
                <div class="issue">

                    <span class="badge">
                        ${escapeHtml(i.category)}
                    </span>

                    <p>
                        <b>
                            ${escapeHtml(i.text)}
                        </b>
                    </p>

                    <p>
                        ${escapeHtml(i.explanation)}
                    </p>

                    <p>
                        <b>수정 방향</b>
                        <br>
                        ${escapeHtml(i.direction)}
                    </p>
            `;

            if (i.alternatives?.length) {

                html += `
                    <div class="alternatives">
                        ${i.alternatives
                        .map(a => `
                                <span class="alt">
                                    ${escapeHtml(a)}
                                </span>
                            `)
                        .join('')}
                    </div>
                `;
            }

            html += `
                </div>
            `;
        });
    }


    // -----------------------------------------------------
    // 스스로 생각해볼 질문
    // -----------------------------------------------------

    if (x.questions?.length) {

        html += `
            <div class="section-title">
                스스로 생각해볼 질문
            </div>
        `;

        x.questions.forEach(q => {

            html += `
                <div class="question-item">
                    ${escapeHtml(q)}
                </div>
            `;

        });
    }


    body.innerHTML = html;

    sec.classList.remove('hidden');

    sec.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
}


// =========================================================
// HTML 이스케이프
// =========================================================

function escapeHtml(v) {

    return String(v ?? '').replace(
        /[&<>'"]/g,
        c => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[c])
    );
}