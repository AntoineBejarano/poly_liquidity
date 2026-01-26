"""
API endpoints for strategy templates.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, User
from app.models.strategy_template_config import get_template_config, list_template_configs, FieldType
from app.models.external_data_source import ExternalDataSource
from app.database import get_db

router = APIRouter(prefix="/strategy-templates", tags=["strategy-templates"])


@router.get("")
async def list_templates(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Lista todas las plantillas de estrategias disponibles."""
    return list_template_configs()


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Obtiene la configuración de una plantilla de estrategia específica."""
    import logging
    logger = logging.getLogger(__name__)
    
    template_config = get_template_config(template_id)
    if not template_config:
        logger.error(f"Template '{template_id}' not found in TEMPLATE_CONFIGS")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )
    
    logger.info(f"Loading template '{template_id}', template_config type: {type(template_config)}")
    logger.info(f"Template has fields: {hasattr(template_config, 'fields')}, fields count: {len(template_config.fields) if hasattr(template_config, 'fields') and template_config.fields else 0}")
    
    if not hasattr(template_config, 'fields') or not template_config.fields:
        logger.error(f"Template '{template_id}' has no fields attribute or fields is empty")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Template '{template_id}' configuration is invalid: missing fields"
        )
    
    # Get external data sources for select fields
    external_sources = db.query(ExternalDataSource).filter(
        ExternalDataSource.is_active == True
    ).all()
    
    # Build response with fields, replacing dynamic options
    fields = []
    try:
        for field in template_config.fields:
            field_type = field["type"]
            # Handle both Enum and string types
            if isinstance(field_type, FieldType):
                type_value = field_type.value
            else:
                type_value = str(field_type)
            
            field_dict = {
                "key": field["key"],
                "label": field["label"],
                "type": type_value,
                "required": field.get("required", False),
                "description": field.get("description", ""),
                "section": field.get("section", "General"),
                "default": field.get("default"),
            }
            
            # Add type-specific properties
            if isinstance(field_type, FieldType):
                if field_type == FieldType.NUMBER:
                    field_dict["min"] = field.get("min")
                    field_dict["max"] = field.get("max")
                    field_dict["step"] = field.get("step")
                elif field_type == FieldType.SELECT:
                    if field.get("options_source") == "external_data_sources":
                        field_dict["options"] = [
                            {"value": str(src.id), "label": src.name}
                            for src in external_sources
                        ]
                    else:
                        field_dict["options"] = field.get("options", [])
            else:
                # Fallback for string types
                if type_value == "number":
                    field_dict["min"] = field.get("min")
                    field_dict["max"] = field.get("max")
                    field_dict["step"] = field.get("step")
                elif type_value == "select":
                    if field.get("options_source") == "external_data_sources":
                        field_dict["options"] = [
                            {"value": str(src.id), "label": src.name}
                            for src in external_sources
                        ]
                    else:
                        field_dict["options"] = field.get("options", [])
            
            fields.append(field_dict)
    except Exception as e:
        logger.error(f"Error processing fields for template '{template_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing template fields: {str(e)}"
        )
    
    logger.info(f"Template '{template_id}' processed successfully, returning {len(fields)} fields")
    
    return {
        "id": template_config.template_id,
        "name": template_config.name,
        "description": template_config.description,
        "category": template_config.category,
        "fields": fields,
    }


@router.post("/{template_id}/compile")
async def compile_template(
    template_id: str,
    config: Dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compila una configuración de plantilla a Decision Graph y Support Graphs."""
    from app.core.strategy_engine.template_compiler import compile_strategy
    
    try:
        result = compile_strategy(template_id, config)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

