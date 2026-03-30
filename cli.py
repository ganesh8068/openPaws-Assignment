import typer
from rich.console import Console
from rich.table import Table
from models import get_session, Facility, Inspection, Violation, Species
from sqlalchemy import func
from datetime import datetime, timedelta

app = typer.Typer(help="OpenPAWS USDA APHIS Inspection Database CLI")
console = Console()

@app.command()
def critical_violations(company: str, state: str, years: int = 2):
    """
    Get all critical violations for a company in a specific state over the past X years.
    """
    session = get_session()
    cutoff_date = datetime.now().date() - timedelta(days=years*365)
    
    query = session.query(Facility, Inspection, Violation)\
        .join(Inspection, Facility.id == Inspection.facility_id)\
        .join(Violation, Inspection.id == Violation.inspection_id)\
        .filter(Facility.name.ilike(f"%{company}%"))\
        .filter(Facility.state == state)\
        .filter(Violation.severity == "Critical")\
        .filter(Inspection.date >= cutoff_date)
        
    results = query.all()
    
    if not results:
        console.print(f"[yellow]No critical violations found for '{company}' in '{state}' over the last {years} years.[/yellow]")
        return
        
    table = Table(title=f"Critical Violations: {company} ({state})")
    table.add_column("Date", style="cyan")
    table.add_column("Report ID", style="magenta")
    table.add_column("Code", style="red")
    table.add_column("Notes", style="white")
    
    for fac, insp, viol in results:
        notes_preview = viol.notes[:100] + "..." if viol.notes and len(viol.notes) > 100 else viol.notes
        table.add_row(str(insp.date), insp.report_id, viol.violation_type, notes_preview)
        
    console.print(table)

@app.command()
def repeat_violators():
    """
    List facilities with repeat violations (same violation code across multiple inspections).
    """
    session = get_session()
    
    # Query facilities that have > 1 distinct inspection for the same violation type
    subq = session.query(
        Facility.name,
        Facility.customer_id,
        Violation.violation_type,
        func.count(func.distinct(Inspection.id)).label('inspection_count')
    ).join(Inspection, Facility.id == Inspection.facility_id)\
     .join(Violation, Inspection.id == Violation.inspection_id)\
     .group_by(Facility.id, Violation.violation_type)\
     .having(func.count(func.distinct(Inspection.id)) > 1)\
     .subquery()
     
    results = session.query(subq).all()
    
    if not results:
        console.print("[green]No facilities with repeat violations found.[/green]")
        return
        
    table = Table(title="Repeat Violators")
    table.add_column("Facility", style="cyan")
    table.add_column("Customer ID", style="magenta")
    table.add_column("Violation Code", style="red")
    table.add_column("# of Inspections", style="yellow")
    
    for row in results:
        table.add_row(row.name, row.customer_id, row.violation_type, str(row.inspection_count))
        
    console.print(table)

@app.command()
def species_violations(species: str, severity: str = None):
    """
    Get violations affecting a specific species, optionally filtered by severity.
    """
    session = get_session()
    
    query = session.query(Species, Inspection, Violation, Facility)\
        .join(Inspection, Species.inspection_id == Inspection.id)\
        .join(Violation, Inspection.id == Violation.inspection_id)\
        .join(Facility, Inspection.facility_id == Facility.id)\
        .filter(Species.common_name.ilike(f"%{species}%"))
        
    if severity:
        query = query.filter(Violation.severity.ilike(severity))
        
    results = query.all()
    
    if not results:
        console.print(f"[yellow]No violations found for species '{species}'.[/yellow]")
        return
        
    table = Table(title=f"Violations affecting '{species}'")
    table.add_column("Date", style="cyan")
    table.add_column("Facility", style="magenta")
    table.add_column("Species details", style="green")
    table.add_column("Violation", style="red")
    table.add_column("Severity", style="yellow")
    
    # Track unique violations so it doesn't print the same violation if multiple species rows match
    seen_violations = set()
    
    for spec, insp, viol, fac in results:
        v_key = (insp.id, viol.id)
        if v_key in seen_violations:
            continue
        seen_violations.add(v_key)
        
        species_details = f"{spec.count} x {spec.common_name}"
        table.add_row(str(insp.date), fac.name, species_details, viol.violation_type, viol.severity)
        
    console.print(table)

if __name__ == "__main__":
    app()
