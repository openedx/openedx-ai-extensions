precommit:
	npm run lint
	npm run types
	npm audit

requirements:
	npm ci

build:
	rm -rf ./dist
	./node_modules/.bin/fedx-scripts babel src --out-dir dist --source-maps --extensions '.js,.jsx,.ts,.tsx' --ignore '**/*.test.jsx,**/*.test.js,**/*.test.ts,**/*.test.tsx,**/setupTest.js,**/setupTest.ts' --copy-files
	@find dist -name '*.test.*' -delete
	./node_modules/.bin/tsc -p tsconfig.build.json --emitDeclarationOnly
	cp ./LICENSE ./dist/LICENSE 2>/dev/null || cp ../LICENSE ./dist/LICENSE 2>/dev/null || true
	cp ./README.md ./dist/README.md

.PHONY: validate
validate:
	npm run lint -- --max-warnings 0
	npm run types
	npm test
	make build

.PHONY: validate.ci
validate.ci:
	npm ci
	make validate
