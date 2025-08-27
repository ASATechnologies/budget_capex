### Budget Capex

Budget Capex introduces the `Capital Expenditure` doctype and a `Capital Expenditure` accounting dimension. 

It also allows you to create budgets and select accounts that are of type `Fixed Asset` or accounts with report type of `Profit And Loss`. 

It also comes with typical `Monthly Distribution` examples like `1st Quarter`, `January` etc to help you quickly plan your budget.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH

bench get-app https://github.com/ASATechnologies/budget_capex --branch develop

bench install-app budget_capex
```


### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/budget_capex
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
