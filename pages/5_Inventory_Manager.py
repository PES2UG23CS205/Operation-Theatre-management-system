import streamlit as st
from auth import require_auth
from db import get_session, InventoryItem, SurgeryInventoryUsage, Surgery

def render():
    require_auth(["Inventory"])  # strict isolation
    st.title("📦 Inventory — Stock & Usage")

    left, right = st.columns(2)

    # ------- Items (list + add/update)
    with left:
        st.subheader("Items")
        with get_session() as db:
            items = db.query(InventoryItem).all()

        if items:
            for it in items:
                st.write(f"**{it.sku}** — {it.name} ({it.stock_qty}{it.unit}) | Threshold {it.threshold}")
        else:
            st.info("No items yet. Add one below.")

        with st.form("add_item"):
            name = st.text_input("Name")
            sku = st.text_input("SKU")
            cat = st.text_input("Category")
            qty = st.number_input("Stock Qty", min_value=0, step=1)
            thr = st.number_input("Low Stock Threshold", min_value=0, step=1)
            unit = st.text_input("Unit", value="pcs")
            save = st.form_submit_button("Save Item")

        if save:
            if not (name and sku and cat):
                st.error("Name, SKU, and Category are required.")
            else:
                with get_session() as db:
                    ex = db.query(InventoryItem).filter(InventoryItem.sku == sku).first()
                    if ex:
                        ex.name, ex.category, ex.stock_qty, ex.threshold, ex.unit = name, cat, qty, thr, unit
                    else:
                        db.add(InventoryItem(name=name, sku=sku, category=cat, stock_qty=qty, threshold=thr, unit=unit))
                    db.commit()
                st.success("Saved item")

    # ------- Usage (restricted to Scheduled / In-Progress)
    with right:
        st.subheader("Record Usage")
        with get_session() as db:
            items = db.query(InventoryItem).all()
            surgeries = (
                db.query(Surgery)
                .filter(Surgery.status.in_(["Scheduled", "In-Progress"]))
                .order_by(Surgery.date, Surgery.start_time)
                .all()
            )
        if not items or not surgeries:
            st.info("Need at least one item and one eligible surgery to record usage.")
        else:
            it_sel = st.selectbox("Item", [f"{i.id}:{i.name}" for i in items])
            su_sel = st.selectbox("Surgery", [f"{s.id}:{s.procedure} ({s.date})" for s in surgeries])
            qty = st.number_input("Qty Used", min_value=0, step=1)

            if st.button("Record"):
                iid = int(it_sel.split(":")[0])
                sid = int(su_sel.split(":")[0])
                with get_session() as db:
                    it = db.get(InventoryItem, iid)
                    if qty <= 0:
                        st.error("Quantity must be greater than zero.")
                    elif it.stock_qty < qty:
                        st.error("Insufficient stock.")
                    else:
                        it.stock_qty -= qty
                        db.add(SurgeryInventoryUsage(surgery_id=sid, item_id=iid, qty_used=qty))
                        db.commit()
                        st.success("Usage recorded & stock updated")

        st.divider()
        st.subheader("Low Stock Alerts")
        with get_session() as db:
            low = db.query(InventoryItem).filter(InventoryItem.stock_qty <= InventoryItem.threshold).all()
        if low:
            for it in low:
                st.warning(f"{it.name} low: {it.stock_qty}{it.unit} ≤ threshold {it.threshold}")
        else:
            st.success("All good. No low stock items.")
