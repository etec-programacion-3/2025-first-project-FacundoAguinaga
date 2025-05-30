from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware  # 👈 Importar CORS
from tortoise.contrib.fastapi import register_tortoise
from tortoise.models import Model
from tortoise import fields
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Configuración de la aplicación FastAPI
app = FastAPI(
    title="Sistema de Gestión de Biblioteca",
    description="API REST para gestionar libros de una biblioteca escolar",
    version="1.0.0"
)

# 👈 CONFIGURAR CORS - ¡ESTO ES LO QUE NECESITAS!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción deberías especificar los dominios exactos
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],  # Permite todos los headers
)

# Modelo de base de datos con Tortoise ORM
class Libro(Model):
    id = fields.IntField(pk=True)
    titulo = fields.CharField(max_length=255)
    autor = fields.CharField(max_length=255)
    isbn = fields.CharField(max_length=13, unique=True)
    categoria = fields.CharField(max_length=100)
    estado = fields.CharField(max_length=50, default="disponible")  # disponible, prestado, etc.
    fecha_creacion = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "libros"

# Modelos Pydantic para validación de datos
class LibroCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255, description="Título del libro")
    autor: str = Field(..., min_length=1, max_length=255, description="Autor del libro")
    isbn: str = Field(..., min_length=10, max_length=13, description="ISBN del libro")
    categoria: str = Field(..., min_length=1, max_length=100, description="Categoría del libro")
    estado: Optional[str] = Field("disponible", description="Estado del libro")

class LibroUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    autor: Optional[str] = Field(None, min_length=1, max_length=255)
    isbn: Optional[str] = Field(None, min_length=10, max_length=13)
    categoria: Optional[str] = Field(None, min_length=1, max_length=100)
    estado: Optional[str] = Field(None)

class LibroResponse(BaseModel):
    id: int
    titulo: str
    autor: str
    isbn: str
    categoria: str
    estado: str
    fecha_creacion: datetime

    class Config:
        from_attributes = True

# ENDPOINTS DE LA API

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz de bienvenida"""
    return {"mensaje": "API de Gestión de Biblioteca - Fase 1: Libros"}

@app.get("/libros", response_model=List[LibroResponse], tags=["Libros"])
async def listar_libros(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de registros a devolver")
):
    """Listar todos los libros con paginación"""
    libros = await Libro.all().offset(skip).limit(limit)
    return libros

@app.get("/libros/{libro_id}", response_model=LibroResponse, tags=["Libros"])
async def obtener_libro(libro_id: int):
    """Obtener un libro específico por ID"""
    libro = await Libro.get_or_none(id=libro_id)
    if not libro:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    return libro

@app.post("/libros", response_model=LibroResponse, status_code=201, tags=["Libros"])
async def crear_libro(libro_data: LibroCreate):
    """Crear un nuevo libro"""
    try:
        # Verificar si el ISBN ya existe
        libro_existente = await Libro.get_or_none(isbn=libro_data.isbn)
        if libro_existente:
            raise HTTPException(status_code=400, detail="Ya existe un libro con este ISBN")
        
        # Crear el nuevo libro
        libro = await Libro.create(**libro_data.dict())
        return libro
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=400, detail="Ya existe un libro con este ISBN")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/libros/{libro_id}", response_model=LibroResponse, tags=["Libros"])
async def actualizar_libro(libro_id: int, libro_data: LibroUpdate):
    """Actualizar un libro existente"""
    libro = await Libro.get_or_none(id=libro_id)
    if not libro:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    
    try:
        # Actualizar solo los campos proporcionados
        update_data = libro_data.dict(exclude_unset=True)
        if update_data:
            await libro.update_from_dict(update_data)
            await libro.save()
        
        return libro
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=400, detail="Ya existe un libro con este ISBN")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.delete("/libros/{libro_id}", tags=["Libros"])
async def eliminar_libro(libro_id: int):
    """Eliminar un libro"""
    libro = await Libro.get_or_none(id=libro_id)
    if not libro:
        raise HTTPException(status_code=404, detail="Libro no encontrado")
    
    await libro.delete()
    return {"mensaje": "Libro eliminado exitosamente"}

@app.get("/libros/buscar", response_model=List[LibroResponse], tags=["Búsqueda"])
async def buscar_libros(
    titulo: Optional[str] = Query(None, description="Buscar por título"),
    autor: Optional[str] = Query(None, description="Buscar por autor"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    ordenar_por: Optional[str] = Query("titulo", description="Campo por el cual ordenar"),
    orden: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Orden ascendente o descendente"),
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de registros a devolver")
):
    """Buscar y filtrar libros con múltiples criterios"""
    query = Libro.all()
    
    # Aplicar filtros
    if titulo:
        query = query.filter(titulo__icontains=titulo)
    if autor:
        query = query.filter(autor__icontains=autor)
    if categoria:
        query = query.filter(categoria__iexact=categoria)
    if estado:
        query = query.filter(estado__iexact=estado)
    
    # Aplicar ordenamiento
    if orden == "desc":
        ordenar_por = f"-{ordenar_por}"
    
    try:
        query = query.order_by(ordenar_por)
    except:
        # Si el campo no existe, ordenar por título por defecto
        query = query.order_by("titulo")
    
    # Aplicar paginación
    libros = await query.offset(skip).limit(limit)
    return libros

@app.get("/estadisticas", tags=["Estadísticas"])
async def obtener_estadisticas():
    """Obtener estadísticas básicas de la biblioteca"""
    total_libros = await Libro.all().count()
    libros_disponibles = await Libro.filter(estado="disponible").count()
    libros_prestados = await Libro.filter(estado="prestado").count()
    
    # Contar libros por categoría
    categorias = await Libro.all().values_list("categoria", flat=True)
    conteo_categorias = {}
    for categoria in categorias:
        conteo_categorias[categoria] = conteo_categorias.get(categoria, 0) + 1
    
    return {
        "total_libros": total_libros,
        "libros_disponibles": libros_disponibles,
        "libros_prestados": libros_prestados,
        "libros_por_categoria": conteo_categorias
    }

# Configuración de la base de datos
register_tortoise(
    app,
    db_url="sqlite://biblioteca.db",
    modules={"models": ["__main__"]},
    generate_schemas=True,
    add_exception_handlers=True,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)