// Vercel 빌드 단계에서 실행: 환경 변수 API_BASE_URL 을 읽어 config.js 를 생성한다.
// 정적 HTML/JS 는 런타임에 환경 변수를 읽을 수 없기 때문에 빌드 시점에 값을 주입한다.
const fs = require("fs");
const path = require("path");

const apiBaseUrl = (process.env.API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");
const content = `// 자동 생성 파일 (generate-config.js). 직접 수정하지 마세요.
window.APP_CONFIG = { API_BASE_URL: ${JSON.stringify(apiBaseUrl)} };
`;
fs.writeFileSync(path.join(__dirname, "config.js"), content);
console.log(`config.js 생성: API_BASE_URL=${apiBaseUrl}`);
