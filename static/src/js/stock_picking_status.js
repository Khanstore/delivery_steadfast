/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        onMounted(async () => {
            const root = this.model?.root;
            if (!root || root.resModel !== "stock.picking" || !root.resId) {
                return;
            }
            const data = root.data || {};
            const status = (data.steadfast_parcel_status || "").toLowerCase();
            const terminal = data.steadfast_status_terminal;
            if (!data.steadfast_is_carrier || terminal || ["delivered", "cancelled"].includes(status)) {
                return;
            }
            try {
                await this.orm.call("stock.picking", "action_steadfast_refresh_status_if_needed", [[root.resId]]);
                await this.model.root.load();
            } catch (error) {
                // Never block the delivery order because a courier API is unavailable.
                console.warn("Steadfast status refresh skipped:", error);
            }
        });
    },
});
