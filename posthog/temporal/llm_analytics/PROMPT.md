# Better LLM analytics dashboard

I will describe a problem and a desired solution. You will help me implement it in a way that's maintainable, in line with best practices, and with existing code. When in doubt about anything, you will research examples in existing code. You will make sure that examples don't just come from our own product, to avoid skewing them. You will explain the examples you used from me. If in doubt, feel free to ask me after presenting the examples and arguments and I will help you refine the plan. Ultrathink.

## Problem

I am an engineer working on PostHog LLM analytics. We currently have a dashboard that's the page where you land when opening the product. This page has a set of fixed charts, that are note editable or reorderable in any way. Most you can do is "open as new insight", but this will create them as a normal insight that will then live in the prdocut analytics section.

## Solution

We should have the LLM analytics dashboard be customisable. These are features we should like:

- We still want to keep it as a single main view representative of LLM analytics, so not going crazy and adding multiple dashboards and whatnot.
- We have extensive code and product for features like insights and dashboards. It's VERY important to not reinvent the wheel, and be consistent with existing code.
- We should always be able to reset the dashboard to the default state, in case something goes wrong.
- Dragging and reorganising tiles should be possible
- Adding and removing arbitray tiles should be possible
- Duplicating an existinf or template tile and then making some changes to it and adding it to the dashbaord should be easy
- The default dashboard should have a set of sensible charts, but we should also be able to suggest more templates to them that we pre-built but are maybe not applicable to everyone.
- The date filters and whatnot should still work across all LLMA products (i.e. if I set last 14 days in the dashboard and change to the generations tab it should still be applied, and viceversa)
- We should have a way to "spawn" new charts into users dashboards. For instance if we add a new template that makes sense to show by default, it should appear in the dashboard without users having to dig into templates.
