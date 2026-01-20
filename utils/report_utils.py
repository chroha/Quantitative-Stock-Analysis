"""
Report Formatting Utilities
Centralized logic for formatting console and text reports.
"""

def format_financial_score_report(score_data):
    """Format financial score as a clean report string."""
    if not score_data:
        return None
    
    lines = []
    lines.append("-" * 70)
    lines.append("FINANCIAL SCORE REPORT")
    lines.append("-" * 70)
    
    # Check for data warnings
    if 'data_warnings' in score_data:
        for w in score_data['data_warnings']:
             lines.append(f"[NOTE] {w} - Score reliability reduced.")
        lines.append("-" * 70)
        
    lines.append(f"Total Score: {score_data.get('total_score', 0):.1f} / 100")
    lines.append("")
    
    cats = score_data.get('category_scores', {})
    for cat_name, cat_data in cats.items():
        name = cat_name.replace('_', ' ').title()
        score = cat_data.get('score', 0)
        
        # Calculate actual max score based on active weights
        actual_max = 0
        if 'metrics' in cat_data:
            for metric, details in cat_data['metrics'].items():
                if not details.get('disabled', False):
                    actual_max += details.get('weight', 0)
        
        # Use actual max if calculated, otherwise use the stored max
        display_max = actual_max if actual_max > 0 else cat_data.get('max', 0)
        
        # Cap displayed score to max (handle sector weight overrides)
        display_score = min(score, display_max) if display_max > 0 else score
        
        lines.append(f"  {name:<20} : {display_score:>5.1f} / {display_max}")
        
        # Metrics detail
        if 'metrics' in cat_data:
            for metric, details in cat_data['metrics'].items():
                val = details.get('value')
                
                # Format value
                if isinstance(val, float):
                    if abs(val) < 1:
                        val_str = f"{val:.2%}"
                    else:
                        val_str = f"{val:.2f}"
                else:
                    val_str = str(val) if val is not None else "N/A"
                
                # Check if disabled
                if details.get('disabled', False):
                    note = details.get('note', 'Not used for this sector')
                    lines.append(f"      - {metric:<24}: {val_str:>10} ({note})")
                    continue
                
                weighted = details.get('weighted_score', 0)
                weight = details.get('weight', 0)
                lines.append(f"      - {metric:<24}: {val_str:>10} (Score: {weighted} / {weight})")
    
    lines.append("-" * 70)
    return "\n".join(lines)


def format_technical_score_report(score_data):
    """Format technical score as a clean report string."""
    if not score_data:
        return None
    
    lines = []
    lines.append("-" * 70)
    lines.append("TECHNICAL SCORE REPORT")
    lines.append("-" * 70)
    total = score_data.get('total_score', 0)
    max_score = score_data.get('max_score', 100)
    lines.append(f"Total Score: {total} / {max_score}")
    lines.append("")
    
    cats = score_data.get('categories', {})
    for cat_name, cat_data in cats.items():
        name = cat_name.replace('_', ' ').title()
        earned = cat_data.get('earned_points', 0)
        max_pts = cat_data.get('max_points', 0)
        lines.append(f"  {name:<20} : {earned:>5} / {max_pts}")
        
        # Indicators detail
        if 'indicators' in cat_data:
            for ind, details in cat_data['indicators'].items():
                score = details.get('score', 0)
                max_ind = details.get('max_score', 0)
                signal = details.get('explanation', details.get('signal', ''))
                
                # Find the primary value - try common key patterns
                val = None
                for key in [ind, 'value', 'rsi', 'macd', 'adx', 'atr', 'roc', 'obv', 
                           'current_price', 'position', 'bandwidth', 'volume_ratio']:
                    if key in details and key != 'score' and key != 'max_score':
                        candidate = details.get(key)
                        if isinstance(candidate, (int, float)) and val is None:
                            val = candidate
                            break
                
                if isinstance(val, float):
                    val_str = f"{val:.2f}"
                elif val is not None:
                    val_str = str(val)
                else:
                    val_str = f"{score}/{max_ind}"
                
                # Truncate long signals
                if len(signal) > 50:
                    signal = signal[:47] + "..."
                lines.append(f"      - {ind:<20}: {val_str:>10} ({signal})")
    
    lines.append("-" * 70)
    return "\n".join(lines)


def format_valuation_report(val_result):
    """Format valuation result as a clean report string."""
    if not val_result:
        return None
    
    ticker = val_result.get('ticker', '?')
    sector = val_result.get('sector', 'Unknown')
    current_price = val_result.get('current_price')
    weighted_fv = val_result.get('weighted_fair_value')
    price_diff = val_result.get('price_difference_pct')
    methods = val_result.get('method_results', {})
    confidence = val_result.get('confidence', {})
    
    lines = []
    lines.append("-" * 70)
    lines.append(f"VALUATION REPORT - {ticker} ({sector})")
    lines.append("-" * 70)
    
    if current_price:
        lines.append(f"Current Price: ${current_price:.2f}")
    
    if methods:
        lines.append("")
        lines.append("Valuation Methods:")
        sorted_methods = sorted(methods.items(), key=lambda x: x[1].get('weight', 0), reverse=True)
        for method_name, result in sorted_methods:
            model_name = result['model_name']
            fair_value = result.get('fair_value')
            weight = result.get('weight', 0)
            upside = result.get('upside_pct')
            status = result.get('status', 'success')
            
            # Handle failed models
            if status == 'failed' or fair_value is None:
                reason = result.get('reason', 'Unable to calculate')
                lines.append(f"  {model_name:20s}      N/A   (Weight: {weight*100:>3.0f}%)  [{reason}]")
                continue
            
            upside_str = f"{'+'if upside >= 0 else ''}{upside:.1f}%"
            if weight > 0:
                lines.append(f"  {model_name:20s} ${fair_value:>8.2f}  (Weight: {weight*100:>3.0f}%)  [{upside_str:>7s}]")
            else:
                lines.append(f"  {model_name:20s} ${fair_value:>8.2f}  (Weight:   0%)  [Not used]")
    
    if weighted_fv:
        lines.append("")
        lines.append(f"Weighted Fair Value: ${weighted_fv:.2f}")
    
    if price_diff is not None:
        diff_str = f"{'+'if price_diff >= 0 else ''}{price_diff:.1f}%"
        if price_diff > 20:
            assessment = "Significantly Undervalued"
        elif price_diff > 10:
            assessment = "Undervalued"
        elif price_diff > -10:
            assessment = "Fairly Valued"
        elif price_diff > -20:
            assessment = "Overvalued"
        else:
            assessment = "Significantly Overvalued"
        lines.append(f"Price Difference: {diff_str} ({assessment})")
    
    if confidence:
        methods_used = confidence.get('methods_used', 0)
        methods_total = confidence.get('methods_available', 0)
        lines.append(f"Confidence: {methods_used}/{methods_total} methods available")
    
    lines.append("-" * 70)
    return "\n".join(lines)
