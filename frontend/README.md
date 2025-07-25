README

Installation:

At the frontend-app-<application> you need to add


```js
const path = require('path');

module.exports = {
  localModules: [
    {
      moduleName: '@openedx/openedx-aiext-ui',
      dir: path.resolve(__dirname, '../openedx-ai-extensions/frontend'),
      dist: 'src',
    },
  ],
};
```

Then add a plugin slot such as:

```js
    'org.openedx.frontend.learning.unit_title.v1': {
      keepDefault: true,
      plugins: [
        {
          op: PLUGIN_OPERATIONS.Insert,
          widget: {
            id: 'ai-red-line',
            type: DIRECT_PLUGIN,
            priority: 10,
            RenderWidget: RedLine,
          },
        },
      ],
```