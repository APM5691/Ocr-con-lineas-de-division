<?php

require_once 'conexion.php';

try {
    $pdo = conectarBaseDatos();
    
    echo "<h2>✅ Conexión exitosa a PostgreSQL</h2>";
    
    // Ejemplo: crear tabla
    $pdo->exec("CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nombre VARCHAR(100),
        email VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )");
    
    // Ejemplo: insertar datos
    $stmt = $pdo->prepare("INSERT INTO usuarios (nombre, email) VALUES (?, ?)");
    $stmt->execute(['Juan Pérez', 'juan@example.com']);
    
    // Ejemplo: consultar datos
    $stmt = $pdo->query("SELECT * FROM usuarios");
    $usuarios = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    echo "<h3>Usuarios en la base de datos:</h3>";
    echo "<ul>";
    foreach ($usuarios as $user) {
        echo "<li>{$user['nombre']} - {$user['email']}</li>";
    }
    echo "</ul>";
    
} catch (PDOException $e) {
    echo "<h2>❌ Error de conexión: " . $e->getMessage() . "</h2>";
}
?>