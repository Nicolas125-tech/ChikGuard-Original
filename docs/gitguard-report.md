> 🔒 **Localização e sugestão de correção disponíveis no PROguard.** Este relatório FREE mostra o que foi encontrado, não onde nem como corrigir.

# Relatório de Segurança — Nicolas125-tech/ChikGuard-Original

**Scan:** `cmssufmvn00b6mo99q0fr28ks` · MANUAL · branch `main` · commit `3c5d2e7a6eb7`
**Status:** COMPLETED · **Executado em:** 2026-08-14T11:09:08.877Z · **Concluído em:** 2026-08-14T11:12:01.759Z
**Relatório gerado em:** 2026-08-14T11:13:56.679Z por GitGuard

## Instruções para a IA que for corrigir isto

- Repositório alvo: Nicolas125-tech/ChikGuard-Original, branch "main", commit 3c5d2e7a6eb7c10df9afc112daf5873f480ed39a. Aplique as correções diretamente nesse checkout.
- Em "dependencyUpgrades", cada entrada agrupa TODOS os CVEs de um mesmo pacote — faça UM upgrade por pacote (para "recommendedVersion" ou mais recente), não uma correção por CVE.
- Em "secrets", nunca tente adivinhar ou reconstruir o valor original do segredo (ele foi propositalmente redigido) — apenas remova/rotacione conforme "remediation".
- Depois de aplicar as correções, rode os testes existentes do projeto e, se disponível, o linter/build antes de considerar concluído.

## Resumo

- **Total de findings:** 163
- **Por severidade:** CRITICAL: 2 · HIGH: 72 · MEDIUM: 77 · LOW: 12
- **Por scanner:** TRIVY: 131 · SEMGREP: 22 · GITLEAKS: 10

## Dependências para atualizar

### 📦 `shell-quote` (2 CVEs) — severidade máxima: CRITICAL

**Ação recomendada:** atualizar de `1.8.3` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| CRITICAL | CVE-2026-9277 | shell-quote: shell-quote: Arbitrary code execution via command injection due to unescaped line terminators | — |
| HIGH | CVE-2026-13311 | shell-quote: shell-quote/parse: shell-quote: Denial of Service due to inefficient input parsing | — |

### 📦 `tar` (12 CVEs) — severidade máxima: CRITICAL

**Ação recomendada:** atualizar de `6.2.1` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| CRITICAL | CVE-2026-59873 | tar: node-tar: Denial of Service via crafted gzip bomb | — |
| HIGH | CVE-2026-23745 | node-tar: tar: node-tar: Arbitrary file overwrite and symlink poisoning via unsanitized linkpaths in archives | — |
| HIGH | CVE-2026-23950 | node-tar: tar: node-tar: Arbitrary file overwrite via Unicode path collision race condition | — |
| HIGH | CVE-2026-24842 | node-tar: tar: node-tar: Arbitrary file creation via path traversal bypass in hardlink security check | — |
| HIGH | CVE-2026-26960 | node-tar: node-tar: Arbitrary file read/write via malicious archive hardlink creation | — |
| HIGH | CVE-2026-29786 | node-tar: hardlink path traversal via drive-relative linkpath | — |
| HIGH | CVE-2026-31802 | tar: tar: File overwrite via drive-relative symlink traversal | — |
| HIGH | CVE-2026-59874 | tar: Node-tar: Denial of Service via malformed tar archive header | — |
| MEDIUM | CVE-2026-53655 | node-tar: node-tar: File smuggling due to inconsistent tar archive parsing | — |
| MEDIUM | CVE-2026-59871 | node-tar: node-tar: Denial of Service due to incorrect PAX path handling | — |
| MEDIUM | CVE-2026-59875 | node-tar: node-tar: Denial of Service via crafted archive with NUL bytes in metadata | — |
| MEDIUM | — | node-tar: Uncontrolled recursion in mapHas/filesFilter allows uncatchable stack-overflow DoS via crafted long-path tar with member selection | — |

### 📦 `xlsx` (4 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `0.18.5` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2024-22363 | SheetJS Regular Expression Denial of Service (ReDoS) | — |
| HIGH | CVE-2023-30533 | Prototype Pollution in sheetJS | — |
| HIGH | CVE-2024-22363 | SheetJS Regular Expression Denial of Service (ReDoS) | — |
| HIGH | CVE-2023-30533 | Prototype Pollution in sheetJS | — |

### 📦 `@babel/plugin-transform-modules-systemjs` (1 CVE) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `7.29.0` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-44728 | Babel is a compiler for writing next generation JavaScript. From 7.12. ... | — |

### 📦 `@xmldom/xmldom` (10 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `0.7.13` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-34601 | xmldom: xmldom: XML structure injection via CDATA terminator | — |
| HIGH | CVE-2026-41672 | xmldom: @xmldom/xmldom: xmldom: Arbitrary XML Node Injection | — |
| HIGH | CVE-2026-41673 | @xmldom/xmldom: xmldom: xmldom: Denial of Service via deeply nested XML documents | — |
| HIGH | CVE-2026-41674 | xmldom: xmldom: Arbitrary XML markup injection | — |
| HIGH | CVE-2026-41675 | xmldom: xmldom: Arbitrary XML node injection via crafted processing instructions | — |
| HIGH | CVE-2026-34601 | xmldom: xmldom: XML structure injection via CDATA terminator | — |
| HIGH | CVE-2026-41672 | xmldom: @xmldom/xmldom: xmldom: Arbitrary XML Node Injection | — |
| HIGH | CVE-2026-41673 | @xmldom/xmldom: xmldom: xmldom: Denial of Service via deeply nested XML documents | — |
| HIGH | CVE-2026-41674 | xmldom: xmldom: Arbitrary XML markup injection | — |
| HIGH | CVE-2026-41675 | xmldom: xmldom: Arbitrary XML node injection via crafted processing instructions | — |

### 📦 `brace-expansion` (3 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `1.1.12` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-13149 | brace-expansion: Brace-expansion: Denial of Service due to exponential-time complexity | — |
| HIGH | CVE-2026-14257 | brace-expansion through 5.0.7 is vulnerable to denial of service via m ... | — |
| MEDIUM | CVE-2026-33750 | brace-expansion: brace-expansion: Denial of Service via zero step value in brace pattern | — |

### 📦 `form-data` (3 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `3.0.4` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-12143 | form-data: form-data: Form field override via CRLF injection | — |
| HIGH | CVE-2026-12143 | form-data: form-data: Form field override via CRLF injection | — |
| HIGH | CVE-2026-12143 | form-data: form-data: Form field override via CRLF injection | — |

### 📦 `js-yaml` (4 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `3.14.2` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-59869 | js-yaml: js-yaml: Denial of Service via crafted YAML documents | — |
| HIGH | CVE-2026-59869 | js-yaml: js-yaml: Denial of Service via crafted YAML documents | — |
| MEDIUM | CVE-2026-53550 | js-yaml: js-yaml: Denial of Service via crafted YAML merge keys | — |
| MEDIUM | CVE-2026-53550 | js-yaml: js-yaml: Denial of Service via crafted YAML merge keys | — |

### 📦 `lodash` (4 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `4.17.23` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-4800 | lodash: lodash: Arbitrary code execution via untrusted input in template imports | — |
| HIGH | CVE-2026-4800 | lodash: lodash: Arbitrary code execution via untrusted input in template imports | — |
| MEDIUM | CVE-2026-2950 | lodash: Lodash: Prototype pollution allows deletion of built-in prototype properties via array path bypass | — |
| MEDIUM | CVE-2026-2950 | lodash: Lodash: Prototype pollution allows deletion of built-in prototype properties via array path bypass | — |

### 📦 `minimatch` (3 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `3.1.2` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-26996 | minimatch: minimatch: Denial of Service via specially crafted glob patterns | — |
| HIGH | CVE-2026-27903 | minimatch: minimatch: Denial of Service due to unbounded recursive backtracking via crafted glob patterns | — |
| HIGH | CVE-2026-27904 | minimatch: Minimatch: Denial of Service via catastrophic backtracking in glob expressions | — |

### 📦 `node-forge` (4 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `1.3.3` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-33891 | node-forge: node-forge: Denial of Service via infinite loop in BigInteger.modInverse() | — |
| HIGH | CVE-2026-33894 | node-forge: Forge: Signature Forgery via Weak RSASSA PKCS#1 v1.5 Verification | — |
| HIGH | CVE-2026-33895 | node-forge: Forge: Authentication bypass via forged Ed25519 cryptographic signatures | — |
| HIGH | CVE-2026-33896 | node-forge: Forge (node-forge): Certificate validation bypass allows unauthorized certificate issuance | — |

### 📦 `picomatch` (4 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `2.3.1` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-33671 | picomatch: Picomatch: Regular Expression Denial of Service via crafted extglob patterns | — |
| HIGH | CVE-2026-33671 | picomatch: Picomatch: Regular Expression Denial of Service via crafted extglob patterns | — |
| MEDIUM | CVE-2026-33672 | picomatch: Picomatch: Data integrity compromised via method injection with crafted POSIX bracket expressions | — |
| MEDIUM | CVE-2026-33672 | picomatch: Picomatch: Data integrity compromised via method injection with crafted POSIX bracket expressions | — |

### 📦 `semver` (1 CVE) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `7.3.2` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2022-25883 | nodejs-semver: Regular expression denial of service | — |

### 📦 `ws` (7 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `6.2.3` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-48779 | ws: ws: Denial of Service via memory exhaustion from small WebSocket fragments | — |
| HIGH | CVE-2026-48779 | ws: ws: Denial of Service via memory exhaustion from small WebSocket fragments | — |
| HIGH | CVE-2026-48779 | ws: ws: Denial of Service via memory exhaustion from small WebSocket fragments | — |
| HIGH | CVE-2026-48779 | ws: ws: Denial of Service via memory exhaustion from small WebSocket fragments | — |
| HIGH | CVE-2026-48779 | ws: ws: Denial of Service via memory exhaustion from small WebSocket fragments | — |
| MEDIUM | CVE-2026-45736 | ws: ws: Uninitialized memory disclosure via `websocket.close()` with `TypedArray` | — |
| MEDIUM | CVE-2026-45736 | ws: ws: Uninitialized memory disclosure via `websocket.close()` with `TypedArray` | — |

### 📦 `axios` (38 CVEs) — severidade máxima: HIGH

**Ação recomendada:** atualizar de `1.13.5` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| HIGH | CVE-2026-42033 | axios: Axios: HTTP Transport Hijacking via Prototype Pollution | — |
| HIGH | CVE-2026-42035 | axios: Axios: Arbitrary HTTP header injection via prototype pollution | — |
| HIGH | CVE-2026-42043 | axios: Axios: NO_PROXY bypass via crafted URL | — |
| HIGH | CVE-2026-42264 | axios: Axios: Prototype pollution allows information disclosure and request manipulation | — |
| HIGH | CVE-2026-44486 | axios: Axios: Information disclosure of proxy credentials via HTTP redirects | — |
| HIGH | CVE-2026-44487 | axios: Axios: Information disclosure of proxy credentials via redirect flows | — |
| HIGH | CVE-2026-44488 | axios: Axios: Denial of Service due to unenforced request and response size limits | — |
| HIGH | CVE-2026-44494 | axios: Axios: Man-in-the-Middle (MITM) attack via Prototype Pollution | — |
| HIGH | CVE-2026-44495 | axios: Axios: Information disclosure due to prototype pollution vulnerability | — |
| HIGH | CVE-2026-44496 | axios: Axios: Client-side Denial of Service via unescaped regex metacharacters in XSRF cookie name | — |
| HIGH | — | Axios Node HTTP adapter can use an inherited proxy after interceptor config cloning | — |
| MEDIUM | — | Axios: Excessive recursion in formDataToJSON can cause denial of service | — |
| MEDIUM | — | Axios: Nested axios option objects can consume polluted prototype values | — |
| MEDIUM | — | Axios: NO_PROXY bypass for 0.0.0.0 local addresses in axios | — |
| MEDIUM | — | Axios form serializer maxDepth bypass via {} metatoken | — |
| MEDIUM | — | Axios: Fetch adapter `ReadableStream` uploads bypass `maxBodyLength` | — |
| MEDIUM | — | Axios: Prototype pollution gadgets can alter axios request construction | — |
| MEDIUM | — | Axios: HTTP/2 streamed uploads bypass `maxBodyLength` | — |
| MEDIUM | — | Axios: Deep formToJSON Key Recursion Can Cause Denial of Service | — |
| MEDIUM | — | Axios: Prototype pollution auth subfields can inject Basic auth | — |
| MEDIUM | CVE-2025-62718 | axios: Axios: Server-Side Request Forgery and proxy bypass due to improper hostname normalization | — |
| MEDIUM | CVE-2026-40175 | axios: Axios: Remote Code Execution via Prototype Pollution escalation | — |
| MEDIUM | CVE-2026-42034 | axios: Axios: Denial of Service via oversized streamed uploads bypassing body limits | — |
| MEDIUM | CVE-2026-42036 | axios: Axios: Denial of Service via unbounded stream consumption when 'responseType: 'stream'' is used | — |
| MEDIUM | CVE-2026-42037 | axios: Node.js: Axios: Information disclosure via CRLF injection in multipart Content-Type header | — |
| MEDIUM | CVE-2026-42038 | axios: Axios: Information disclosure due to `no_proxy` bypass | — |
| MEDIUM | CVE-2026-42039 | axios: Node.js: Axios: Denial of Service via unbounded recursion in toFormData with deeply nested request data | — |
| MEDIUM | CVE-2026-42041 | axios: Axios: Authentication bypass due to prototype pollution of HTTP error handling | — |
| MEDIUM | CVE-2026-42042 | axios: Axios: XSRF token bypass leading to information disclosure | — |
| MEDIUM | CVE-2026-42044 | axios: Axios: Invisible JSON Response Tampering via Prototype Pollution Gadget | — |
| MEDIUM | CVE-2026-44490 | axios: Axios: Information disclosure and denial of service due to prototype pollution | — |
| MEDIUM | — | Axios: Excessive recursion in formDataToJSON can cause denial of service | — |
| MEDIUM | — | Axios: Nested axios option objects can consume polluted prototype values | — |
| MEDIUM | — | Axios: Fetch adapter `ReadableStream` uploads bypass `maxBodyLength` | — |
| MEDIUM | — | Axios: Prototype pollution gadgets can alter axios request construction | — |
| MEDIUM | — | Axios: HTTP/2 streamed uploads bypass `maxBodyLength` | — |
| MEDIUM | — | Axios: Deep formToJSON Key Recursion Can Cause Denial of Service | — |
| LOW | CVE-2026-42040 | axios: Axios: Incorrect null byte handling can lead to data integrity issues | — |

### 📦 `dompurify` (20 CVEs) — severidade máxima: MEDIUM

**Ação recomendada:** atualizar de `3.3.3` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| MEDIUM | CVE-2026-65898 | DOMPurify before 3.4.11 fails to clone the ALLOWED_ATTR allowlist when ... | — |
| MEDIUM | CVE-2026-65902 | DOMPurify before 3.4.7 (affected versions <= 3.4.5) passes direct refe ... | — |
| MEDIUM | CVE-2026-65903 | dompurify: DOMPurify: Security bypass allows injection of malicious content | — |
| MEDIUM | CVE-2026-49978 | dompurify: DOMPurify: Cross-site scripting vulnerability allows code execution | — |
| MEDIUM | CVE-2026-65898 | DOMPurify before 3.4.11 fails to clone the ALLOWED_ATTR allowlist when ... | — |
| MEDIUM | CVE-2026-65902 | DOMPurify before 3.4.7 (affected versions <= 3.4.5) passes direct refe ... | — |
| MEDIUM | CVE-2026-41238 | DOMPurify: DOMPurify: Cross-Site Scripting bypass via prototype pollution | — |
| MEDIUM | CVE-2026-41239 | DOMPurify: Vue 2: DOMPurify: Cross-site scripting due to incomplete sanitization of template expressions | — |
| MEDIUM | CVE-2026-41240 | DOMPurify: DOMPurify: Cross-Site Scripting (XSS) via inconsistent tag sanitization | — |
| MEDIUM | CVE-2026-49458 | dompurify: DOMPurify: Cross-site scripting due to improper sanitization of DOM nodes | — |
| MEDIUM | CVE-2026-49459 | dompurify: DOMPurify: Cross-site scripting bypass allows arbitrary script execution | — |
| MEDIUM | CVE-2026-49978 | dompurify: DOMPurify: Cross-site scripting vulnerability allows code execution | — |
| LOW | CVE-2026-65899 | DOMPurify 3.0.0 before 3.4.9 does not reset the retained Trusted Types ... | — |
| LOW | CVE-2026-65900 | DOMPurify versions >=3.0.0 and before 3.4.8, when configured with SAFE ... | — |
| LOW | CVE-2026-65901 | DOMPurify through 3.4.6 contains a cross-site scripting vulnerability  ... | — |
| LOW | — | DOMPurify: `CUSTOM_ELEMENT_HANDLING` bypasses `afterSanitizeElements` for allowed custom elements. | — |
| LOW | CVE-2026-65899 | DOMPurify 3.0.0 before 3.4.9 does not reset the retained Trusted Types ... | — |
| LOW | CVE-2026-65900 | DOMPurify versions >=3.0.0 and before 3.4.8, when configured with SAFE ... | — |
| LOW | CVE-2026-65901 | DOMPurify through 3.4.6 contains a cross-site scripting vulnerability  ... | — |
| LOW | — | DOMPurify: `CUSTOM_ELEMENT_HANDLING` bypasses `afterSanitizeElements` for allowed custom elements. | — |

### 📦 `follow-redirects` (1 CVE) — severidade máxima: MEDIUM

**Ação recomendada:** atualizar de `1.15.11` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| MEDIUM | — | follow-redirects leaks Custom Authentication Headers to Cross-Domain Redirect Targets | — |

### 📦 `fast-xml-parser` (1 CVE) — severidade máxima: MEDIUM

**Ação recomendada:** atualizar de `4.5.6` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| MEDIUM | CVE-2026-41650 | fast-xml-parser: fast-xml-parser: XML injection via improper escaping of comment and CDATA sequences | — |

### 📦 `joi` (1 CVE) — severidade máxima: MEDIUM

**Ação recomendada:** atualizar de `17.13.3` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| MEDIUM | CVE-2026-48038 | joi: joi: Denial of Service via uncaught RangeError on deeply nested input through recursive link() schemas | — |

### 📦 `qs` (1 CVE) — severidade máxima: MEDIUM

**Ação recomendada:** atualizar de `6.14.2` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| MEDIUM | CVE-2026-8723 | ### Summary    `qs.stringify` throws `TypeError` when called with `arr ... | — |

### 📦 `uuid` (3 CVEs) — severidade máxima: MEDIUM

**Ação recomendada:** atualizar de `3.4.0` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| MEDIUM | CVE-2026-41907 | uuid: uuid: Out-of-bounds write vulnerability impacts data integrity and confidentiality | — |
| MEDIUM | CVE-2026-41907 | uuid: uuid: Out-of-bounds write vulnerability impacts data integrity and confidentiality | — |
| MEDIUM | CVE-2026-41907 | uuid: uuid: Out-of-bounds write vulnerability impacts data integrity and confidentiality | — |

### 📦 `xml2js` (1 CVE) — severidade máxima: MEDIUM

**Ação recomendada:** atualizar de `0.4.23` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| MEDIUM | CVE-2023-0842 | node-xml2js: xml2js is vulnerable to prototype pollution | — |

### 📦 `@babel/core` (1 CVE) — severidade máxima: LOW

**Ação recomendada:** atualizar de `7.29.0` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| LOW | CVE-2026-49356 | @babel/core: @babel/core: Arbitrary file read via sourceMappingURL comment | — |

### 📦 `body-parser` (1 CVE) — severidade máxima: LOW

**Ação recomendada:** atualizar de `1.20.4` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| LOW | CVE-2026-12590 | body-parser: body-parser: Denial of Service via invalid limit option | — |

### 📦 `send` (1 CVE) — severidade máxima: LOW

**Ação recomendada:** atualizar de `0.18.0` para `a versão mais recente` (ou superior).

| Severidade | CVE | Descrição | Corrigido em |
|---|---|---|---|
| LOW | CVE-2024-43799 | send: Code Execution Vulnerability in Send Library | — |

## Segredos expostos

### 🔑 ? — Secret detected: Detected a Generic API Key, potentially exposing access to various services and sensitive operations. (HIGH)

Regra: `generic-api-key`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

### 🔑 ? — Secret detected: Detected a Generic API Key, potentially exposing access to various services and sensitive operations. (HIGH)

Regra: `generic-api-key`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

### 🔑 ? — Secret detected: Detected a Generic API Key, potentially exposing access to various services and sensitive operations. (HIGH)

Regra: `generic-api-key`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

### 🔑 ? — Secret detected: Detected a Generic API Key, potentially exposing access to various services and sensitive operations. (HIGH)

Regra: `generic-api-key`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

### 🔑 ? — Secret detected: Uncovered a JSON Web Token, which may lead to unauthorized access to web applications and sensitive user data. (HIGH)

Regra: `jwt`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

### 🔑 ? — Secret detected: Uncovered a JSON Web Token, which may lead to unauthorized access to web applications and sensitive user data. (HIGH)

Regra: `jwt`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

### 🔑 ? — Secret detected: Uncovered a JSON Web Token, which may lead to unauthorized access to web applications and sensitive user data. (HIGH)

Regra: `jwt`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

### 🔑 ? — Secret detected: Detected a Generic API Key, potentially exposing access to various services and sensitive operations. (HIGH)

Regra: `generic-api-key`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

### 🔑 ? — Secret detected: Detected a Generic API Key, potentially exposing access to various services and sensitive operations. (HIGH)

Regra: `generic-api-key`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

### 🔑 ? — Secret detected: Detected a Generic API Key, potentially exposing access to various services and sensitive operations. (HIGH)

Regra: `generic-api-key`

**Remediação:** Remova o valor do código-fonte e mova para uma variável de ambiente / secret manager. Se for uma credencial real (não um placeholder de exemplo), revogue-a imediatamente — ela já está exposta no histórico do Git mesmo após removida do arquivo atual.

## Outros findings

| Severidade | Scanner | Categoria | Título | Local |
|---|---|---|---|---|
| HIGH | SEMGREP | SAST | Semgrep Finding: rules.generic.secrets.security.detected-jwt-token.detected-jwt-token | — |
| HIGH | SEMGREP | SAST | Semgrep Finding: rules.generic.secrets.security.detected-jwt-token.detected-jwt-token | — |
| HIGH | SEMGREP | SAST | Semgrep Finding: rules.generic.secrets.security.detected-jwt-token.detected-jwt-token | — |
| HIGH | SEMGREP | SAST | Semgrep Finding: rules.dockerfile.security.missing-user.missing-user | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.yaml.github-actions.security.github-actions-mutable-action-tag.github-actions-mutable-action-tag | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.yaml.github-actions.security.github-actions-mutable-action-tag.github-actions-mutable-action-tag | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.yaml.github-actions.security.github-actions-mutable-action-tag.github-actions-mutable-action-tag | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.yaml.github-actions.security.github-actions-mutable-action-tag.github-actions-mutable-action-tag | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.yaml.github-actions.security.github-actions-mutable-action-tag.github-actions-mutable-action-tag | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.yaml.github-actions.security.github-actions-mutable-action-tag.github-actions-mutable-action-tag | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.package_managers.npm.npm-missing-minimum-release-age.npm-missing-minimum-release-age | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.generic.nginx.security.header-redefinition.header-redefinition | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.generic.nginx.security.header-redefinition.header-redefinition | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.generic.nginx.security.header-redefinition.header-redefinition | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.ajinabraham.njsscan.crypto.crypto_node.node_insecure_random_generator | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.ajinabraham.njsscan.crypto.crypto_node.node_insecure_random_generator | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.ajinabraham.njsscan.generic.error_disclosure.generic_error_disclosure | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.ajinabraham.njsscan.generic.error_disclosure.generic_error_disclosure | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.ajinabraham.njsscan.crypto.crypto_node.node_insecure_random_generator | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.python.lang.security.audit.insecure-transport.urllib.insecure-request-object.insecure-request-object | — |
| MEDIUM | SEMGREP | SAST | Semgrep Finding: rules.python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | — |
