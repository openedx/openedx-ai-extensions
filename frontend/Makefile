precommit:
	npm run lint
	npm audit

requirements:
	npm ci

build:
	rm -rf ./dist
	./node_modules/.bin/fedx-scripts babel src --out-dir dist --source-maps --ignore **/*.test.jsx,**/*.test.js,**/setupTest.js --copy-files
	@# --copy-files will bring in everything else that wasn't processed by babel. Remove what we don't want.
	@find dist -name '*.test.js*' -delete
	cp ./package.json ./dist/package.json
	cp ./LICENSE ./dist/LICENSE 2>/dev/null || cp ../LICENSE ./dist/LICENSE 2>/dev/null || true
	cp ./README.md ./dist/README.md
