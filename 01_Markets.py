import streamlit as st
import pandas as pd
from core.db import get_session, Market

st.title("Markets")

session = get_session()

# ✅ EXCLUDE deleted markets
markets = session.query(Market).filter(Market.status != "deleted").all()

session.close()

if markets:
    df = pd.DataFrame(
        [
            {
                "ID": m.id,
                "Module": m.module,
                "Question": m.question,
                "Status": m.status,
                "P(YES)": round(m.current_p_yes, 2),
                "End": m.end_time,
            }
            for m in markets
        ]
    )
    st.dataframe(df)
else:
    st.info("No markets yet. Create one from the Create Market page.")