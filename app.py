from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from model import IPLAuctionPredictor
import os
import pandas as pd
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='frontend/build', static_url_path='')

# CORS configuration for production
if os.environ.get('RENDER'):
    # Production on Render - allow specific frontend URL
    frontend_url = os.environ.get('FRONTEND_URL', 'https://ipl-predictor-frontend.onrender.com')
    CORS(app, resources={
        r"/api/*": {
            "origins": [frontend_url, "http://localhost:3000"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"]
        }
    })
else:
    # Development - allow all
    CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize predictor
predictor = IPLAuctionPredictor()

# Load trained model
try:
    predictor.load_model('model_artifacts')
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    print("Please train the model first by running: python model.py")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': predictor.is_trained
    })

@app.route('/api/predict', methods=['POST'])
def predict():
    """Predict auction price for a player"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = [
            'age', 'role', 'country', 'batting_style', 'bowling_style',
            'domestic_matches', 'innings_batted', 'runs_scored',
            'batting_average', 'batting_strike_rate', 'hundreds', 'fifties',
            'highest_score', 'boundary_percentage', 'overs_bowled',
            'wickets_taken', 'bowling_average', 'economy_rate',
            'bowling_strike_rate', 'five_wicket_hauls', 'best_bowling_wickets',
            'dot_ball_percentage', 'catches', 'stumpings',
            'consistency_rating', 'fitness_score', 'experience_factor',
            'recent_form_rating', 'match_winning_performances',
            'pressure_handling_score'
        ]
        
        # Convert numeric fields
        numeric_fields = [f for f in required_fields if f not in ['role', 'country', 'batting_style', 'bowling_style']]
        for field in numeric_fields:
            if field in data:
                data[field] = float(data[field])
        
        # Make prediction
        result = predictor.predict(data)
        
        return jsonify({
            'success': True,
            'prediction': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/dataset-stats', methods=['GET'])
def dataset_stats():
    """Get dataset statistics"""
    try:
        df = pd.read_csv('players_dataset.csv')
        
        stats = {
            'total_players': len(df),
            'avg_price': round(df['auction_price_lakhs'].mean(), 2),
            'max_price': round(df['auction_price_lakhs'].max(), 2),
            'min_price': round(df['auction_price_lakhs'].min(), 2),
            'role_distribution': df['role'].value_counts().to_dict(),
            'country_distribution': df['country'].value_counts().to_dict(),
            'avg_age': round(df['age'].mean(), 2),
            'total_runs': int(df['runs_scored'].sum()),
            'total_wickets': int(df['wickets_taken'].sum())
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/sample-players', methods=['GET'])
def sample_players():
    """Get sample players for reference"""
    try:
        df = pd.read_csv('players_dataset.csv')
        
        # Get diverse samples
        samples = []
        for role in df['role'].unique():
            role_df = df[df['role'] == role]
            sample = role_df.sample(min(2, len(role_df)))
            samples.append(sample)
        
        result_df = pd.concat(samples)
        
        return jsonify({
            'success': True,
            'players': result_df.to_dict('records')
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/generate-demo-data', methods=['GET'])
def generate_demo_data():
    """Generate realistic demo data for testing"""
    try:
        # Define realistic ranges for different roles
        role = np.random.choice(['Batsman', 'Bowler', 'All-Rounder', 'Wicket-Keeper'])
        country = np.random.choice(['India', 'Australia', 'England', 'South Africa', 'New Zealand', 
                                   'West Indies', 'Pakistan', 'Sri Lanka', 'Bangladesh', 'Afghanistan'])
        
        demo_data = {
            'age': np.random.randint(20, 38),
            'role': role,
            'country': country,
            'batting_style': np.random.choice(['Right-Hand', 'Left-Hand']),
            'bowling_style': np.random.choice(['Right-Arm Fast', 'Left-Arm Fast', 'Right-Arm Medium', 
                                              'Left-Arm Medium', 'Right-Arm Spin', 'Left-Arm Spin', 
                                              'Leg-Spin', 'Off-Spin']),
            'domestic_matches': int(np.random.randint(50, 250)),
        }
        
        # Role-specific stats
        if role in ['Batsman', 'All-Rounder', 'Wicket-Keeper']:
            demo_data.update({
                'innings_batted': int(np.random.randint(40, 200)),
                'runs_scored': int(np.random.randint(800, 8000)),
                'batting_average': round(np.random.uniform(20.0, 55.0), 2),
                'batting_strike_rate': round(np.random.uniform(110.0, 180.0), 2),
                'hundreds': int(np.random.randint(0, 15)),
                'fifties': int(np.random.randint(0, 40)),
                'highest_score': int(np.random.randint(50, 180)),
                'boundary_percentage': round(np.random.uniform(8.0, 25.0), 2),
            })
        else:  # Bowler - lower batting stats
            demo_data.update({
                'innings_batted': int(np.random.randint(10, 80)),
                'runs_scored': int(np.random.randint(50, 1500)),
                'batting_average': round(np.random.uniform(8.0, 25.0), 2),
                'batting_strike_rate': round(np.random.uniform(80.0, 140.0), 2),
                'hundreds': 0,
                'fifties': int(np.random.randint(0, 3)),
                'highest_score': int(np.random.randint(15, 65)),
                'boundary_percentage': round(np.random.uniform(5.0, 15.0), 2),
            })
        
        # Bowling stats
        if role in ['Bowler', 'All-Rounder']:
            demo_data.update({
                'overs_bowled': round(np.random.uniform(200.0, 1200.0), 1),
                'wickets_taken': int(np.random.randint(30, 350)),
                'bowling_average': round(np.random.uniform(18.0, 35.0), 2),
                'economy_rate': round(np.random.uniform(6.5, 9.5), 2),
                'bowling_strike_rate': round(np.random.uniform(15.0, 25.0), 2),
                'five_wicket_hauls': int(np.random.randint(0, 8)),
                'best_bowling_wickets': int(np.random.randint(3, 7)),
                'dot_ball_percentage': round(np.random.uniform(35.0, 55.0), 2),
            })
        else:  # Batsman/WK - minimal bowling
            demo_data.update({
                'overs_bowled': round(np.random.uniform(0.0, 50.0), 1),
                'wickets_taken': int(np.random.randint(0, 15)),
                'bowling_average': round(np.random.uniform(25.0, 45.0), 2),
                'economy_rate': round(np.random.uniform(7.0, 11.0), 2),
                'bowling_strike_rate': round(np.random.uniform(18.0, 35.0), 2),
                'five_wicket_hauls': 0,
                'best_bowling_wickets': int(np.random.randint(0, 3)),
                'dot_ball_percentage': round(np.random.uniform(25.0, 45.0), 2),
            })
        
        # Fielding stats
        demo_data.update({
            'catches': int(np.random.randint(10, 120)),
            'stumpings': int(np.random.randint(0, 40) if role == 'Wicket-Keeper' else np.random.randint(0, 3)),
        })
        
        # Performance metrics (0-100 scale)
        demo_data.update({
            'consistency_rating': round(np.random.uniform(40.0, 95.0), 2),
            'fitness_score': round(np.random.uniform(60.0, 98.0), 2),
            'experience_factor': round(np.random.uniform(30.0, 95.0), 2),
            'recent_form_rating': round(np.random.uniform(40.0, 95.0), 2),
            'match_winning_performances': int(np.random.randint(0, 25)),
            'pressure_handling_score': round(np.random.uniform(45.0, 98.0), 2),
        })
        
        return jsonify({
            'success': True,
            'data': demo_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    """Upload and parse CSV file with player data"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Please upload a CSV file.'
            }), 400
        
        # Read CSV file
        try:
            df = pd.read_csv(file)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error reading CSV file: {str(e)}'
            }), 400
        
        # Check if CSV has data
        if len(df) == 0:
            return jsonify({
                'success': False,
                'error': 'CSV file is empty'
            }), 400
        
        # Get first row of data
        player_data = df.iloc[0].to_dict()
        
        # Define expected columns mapping (CSV column -> form field)
        column_mapping = {
            'player_name': 'player_name',
            'age': 'age',
            'role': 'role',
            'country': 'country',
            'batting_style': 'batting_style',
            'bowling_style': 'bowling_style',
            'domestic_matches': 'domestic_matches',
            'innings_batted': 'innings_batted',
            'runs_scored': 'runs_scored',
            'batting_average': 'batting_average',
            'batting_strike_rate': 'batting_strike_rate',
            'hundreds': 'hundreds',
            'fifties': 'fifties',
            'highest_score': 'highest_score',
            'boundary_percentage': 'boundary_percentage',
            'overs_bowled': 'overs_bowled',
            'wickets_taken': 'wickets_taken',
            'bowling_average': 'bowling_average',
            'economy_rate': 'economy_rate',
            'bowling_strike_rate': 'bowling_strike_rate',
            'five_wicket_hauls': 'five_wicket_hauls',
            'best_bowling_wickets': 'best_bowling_wickets',
            'dot_ball_percentage': 'dot_ball_percentage',
            'catches': 'catches',
            'stumpings': 'stumpings',
            'consistency_rating': 'consistency_rating',
            'fitness_score': 'fitness_score',
            'experience_factor': 'experience_factor',
            'recent_form_rating': 'recent_form_rating',
            'match_winning_performances': 'match_winning_performances',
            'pressure_handling_score': 'pressure_handling_score'
        }
        
        # Extract and format data
        formatted_data = {}
        missing_columns = []
        
        for csv_col, form_field in column_mapping.items():
            if csv_col in player_data:
                value = player_data[csv_col]
                # Handle NaN values
                if pd.isna(value):
                    formatted_data[form_field] = 0
                else:
                    # Convert to appropriate type
                    if form_field in ['role', 'country', 'batting_style', 'bowling_style', 'player_name']:
                        formatted_data[form_field] = str(value)
                    else:
                        try:
                            # Try to convert to number
                            formatted_data[form_field] = float(value)
                        except:
                            formatted_data[form_field] = 0
            else:
                missing_columns.append(csv_col)
        
        # Set default values for missing columns
        if 'role' not in formatted_data:
            formatted_data['role'] = 'Batsman'
        if 'country' not in formatted_data:
            formatted_data['country'] = 'India'
        if 'batting_style' not in formatted_data:
            formatted_data['batting_style'] = 'Right-Hand'
        if 'bowling_style' not in formatted_data:
            formatted_data['bowling_style'] = 'Right-Arm Fast'
        
        return jsonify({
            'success': True,
            'data': formatted_data,
            'message': f'Data loaded successfully from CSV',
            'missing_columns': missing_columns if missing_columns else None,
            'total_rows': len(df)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

# Serve React frontend (only needed if serving frontend from same server)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Check if we're serving a built frontend
    if app.static_folder and os.path.exists(app.static_folder):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            index_path = os.path.join(app.static_folder, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(app.static_folder, 'index.html')
    
    # If no frontend build exists, return API info
    return jsonify({
        'message': 'IPL Auction Predictor API',
        'status': 'Backend running',
        'endpoints': {
            'health': '/api/health',
            'predict': '/api/predict (POST)',
            'stats': '/api/dataset-stats',
            'demo': '/api/generate-demo-data',
            'upload': '/api/upload-csv (POST)'
        }
    })

if __name__ == '__main__':
    # Get port from environment variable (for Render)
    port = int(os.environ.get('PORT', 5000))
    
    # Run on localhost or production
    if os.environ.get('RENDER'):
        # Production on Render
        print("="*60)
        print("IPL Auction Price Predictor - PRODUCTION")
        print(f"Port: {port}")
        print("="*60)
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Development
        print("="*60)
        print("IPL Auction Price Predictor - DEVELOPMENT")
        print(f"Server running on: http://localhost:{port}")
        print("API Endpoints:")
        print("  - GET  /api/health         : Health check")
        print("  - POST /api/predict        : Predict player price")
        print("  - GET  /api/dataset-stats  : Get dataset statistics")
        print("  - GET  /api/sample-players : Get sample players")
        print("  - GET  /api/generate-demo-data : Generate demo data")
        print("  - POST /api/upload-csv     : Upload player CSV")
        print("="*60)
        app.run(debug=True, host='0.0.0.0', port=port)
