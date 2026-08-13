# Domain Services Context

This folder is reserved for pure policies spanning multiple domain model types when
no single model/rules module can own them. Most behavior belongs in `engine`; do not
create a service solely to wrap one function or anticipate future use.
