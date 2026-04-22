"""Shop management — profile, customer intake, work orders, triage, invoicing.

Phase 160 opens this package with shop profile CRUD + intake visit
logging (the "arrived on lot" event). Subsequent Track G phases layer
work orders (161), structured issues (162), triage + scheduling
(163-168), invoicing (169), and analytics (171) on top of the
intake_visits row introduced here.
"""

from motodiag.shop.shop_repo import (
    ShopNameExistsError,
    ShopNotFoundError,
    create_shop,
    deactivate_shop,
    delete_shop,
    get_shop,
    get_shop_by_name,
    list_shops,
    update_shop,
)
from motodiag.shop.intake_repo import (
    INTAKE_CLOSE_REASONS,
    INTAKE_STATUSES,
    IntakeAlreadyClosedError,
    IntakeNotFoundError,
    cancel_intake,
    close_intake,
    count_intakes,
    create_intake,
    get_intake,
    list_intakes,
    list_open_for_bike,
    reopen_intake,
    update_intake,
)
from motodiag.shop.work_order_repo import (
    TERMINAL_STATUSES as WORK_ORDER_TERMINAL_STATUSES,
    WORK_ORDER_STATUSES,
    InvalidWorkOrderTransition,
    WorkOrderFKError,
    WorkOrderNotFoundError,
    assign_mechanic,
    cancel_work_order,
    complete_work_order,
    count_work_orders,
    create_work_order,
    get_work_order,
    list_work_orders,
    open_work_order,
    pause_work,
    reopen_work_order,
    require_work_order,
    resume_work,
    start_work,
    unassign_mechanic,
    update_work_order,
)


__all__ = [
    # shop_repo
    "ShopNameExistsError",
    "ShopNotFoundError",
    "create_shop",
    "deactivate_shop",
    "delete_shop",
    "get_shop",
    "get_shop_by_name",
    "list_shops",
    "update_shop",
    # intake_repo
    "INTAKE_CLOSE_REASONS",
    "INTAKE_STATUSES",
    "IntakeAlreadyClosedError",
    "IntakeNotFoundError",
    "cancel_intake",
    "close_intake",
    "count_intakes",
    "create_intake",
    "get_intake",
    "list_intakes",
    "list_open_for_bike",
    "reopen_intake",
    "update_intake",
    # work_order_repo
    "WORK_ORDER_STATUSES",
    "WORK_ORDER_TERMINAL_STATUSES",
    "InvalidWorkOrderTransition",
    "WorkOrderFKError",
    "WorkOrderNotFoundError",
    "assign_mechanic",
    "cancel_work_order",
    "complete_work_order",
    "count_work_orders",
    "create_work_order",
    "get_work_order",
    "list_work_orders",
    "open_work_order",
    "pause_work",
    "reopen_work_order",
    "require_work_order",
    "resume_work",
    "start_work",
    "unassign_mechanic",
    "update_work_order",
]
