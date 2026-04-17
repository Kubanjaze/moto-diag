"""CRM package — customers + customer-vehicle relationships.

Phase 113 (Retrofit): introduces customer relationship management so shops
can track bike owners. Foundation for Track O phase 274 (full CRM) and
Track G phase 160+ (shop intake with customer info).

Placeholder "unassigned" customer (id=1) owns all pre-retrofit vehicles
via migration 006. Real customers are scoped to a user (shop) via
owner_user_id FK so multi-shop deployments don't cross customer data.
"""

from motodiag.crm.models import (
    Customer, CustomerBike, CustomerRelationship,
)
from motodiag.crm.customer_repo import (
    create_customer, get_customer, get_unassigned_customer,
    list_customers, search_customers, update_customer,
    deactivate_customer, count_customers,
    UNASSIGNED_CUSTOMER_ID, UNASSIGNED_CUSTOMER_NAME,
)
from motodiag.crm.customer_bikes_repo import (
    link_customer_bike, unlink_customer_bike,
    list_bikes_for_customer, list_customers_for_bike,
    get_current_owner, transfer_ownership,
)

__all__ = [
    # Models
    "Customer", "CustomerBike", "CustomerRelationship",
    # Customer repo
    "create_customer", "get_customer", "get_unassigned_customer",
    "list_customers", "search_customers", "update_customer",
    "deactivate_customer", "count_customers",
    "UNASSIGNED_CUSTOMER_ID", "UNASSIGNED_CUSTOMER_NAME",
    # Customer-bike repo
    "link_customer_bike", "unlink_customer_bike",
    "list_bikes_for_customer", "list_customers_for_bike",
    "get_current_owner", "transfer_ownership",
]
